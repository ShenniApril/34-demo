#include "preprocess.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <windows.h>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#if defined(__GNUC__) && (defined(__x86_64__) || defined(__i386__)) && !defined(PREPROCESS_SCALAR)
#include <immintrin.h>
#define USE_RUNTIME_AVX2
#endif

namespace {
std::string mode = "identity";
int amount = 0; // Sixteenths of the spatial correction; sharp uses same scale.
int signedRound(int n, int d) { return n < 0 ? -((-n + d/2)/d) : (n + d/2)/d; }

// HVS-inspired heuristic, not a calibrated JND model. Cardinal coherence
// distinguishes supported contours from isolated peaks; clipping and high
// activity are protected. No history, frame labels or encoder state is used.
void perceptualPlane(const uint8_t* s,uint8_t* d,int w,int h,int q,bool balance) {
    const int gain=q<26?std::min(amount,1):amount;
    const int threshold=std::max(8,(32+gain-1)/gain);
#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(4)
#endif
    for(int y=1;y<h-1;++y) for(int x=1;x<w-1;++x) {
        const std::size_t p=std::size_t(y)*w+x;
        const int c=s[p],l=s[p-1],r=s[p+1],u=s[p-w],v=s[p+w];
        if(c<24||c>231)continue; // Protect deep shadows/highlights and clipping.
        const int g=std::abs(l-r)+std::abs(u-v);
        const int activity=std::abs(l-c)+std::abs(r-c)+std::abs(u-c)+std::abs(v-c);
        const int residual=4*c-l-r-u-v;
        int delta=0;
        // Only low/moderate contrast, coherent structures receive enhancement.
        // More changes are allowed at masked luminance extremes, but always +/-1.
        const int maxActivity=(c<64||c>192)?48:36;
        if(g>=6&&g<32&&activity<=maxActivity&&2*g>=activity&&std::abs(residual)>=threshold)
            delta=residual>0?1:-1;
        // Optional isolated-peak suppression in weak-gradient neighborhoods.
        // Both axes must agree on the extremum; no chroma changes are made.
        else if(balance&&g<=4&&activity>=8&&activity<=20&&std::abs(residual)>=12&&
                ((c>l&&c>r&&c>u&&c>v)||(c<l&&c<r&&c<u&&c<v)))
            delta=residual>0?-1:1;
        d[p]=uint8_t(c+delta);
    }
}
#ifdef USE_RUNTIME_AVX2
__attribute__((target("avx2")))
void perceptualPlaneAVX2(const uint8_t* s,uint8_t* d,int w,int h,int q,bool balance) {
    const int gain=q<26?std::min(amount,1):amount;
    const int threshold=std::max(8,(32+gain-1)/gain);
#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(4)
#endif
    for(int y=1;y<h-1;++y) {
        int x=1;
        for(;x+15<w-1;x+=16) {
            const std::size_t p=std::size_t(y)*w+x;
            const auto c=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(s+p)));
            const auto l=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(s+p-1)));
            const auto r=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(s+p+1)));
            const auto u=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(s+p-w)));
            const auto v=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(s+p+w)));
            const auto g=_mm256_add_epi16(_mm256_abs_epi16(_mm256_sub_epi16(l,r)),_mm256_abs_epi16(_mm256_sub_epi16(u,v)));
            const auto activity=_mm256_add_epi16(_mm256_add_epi16(_mm256_abs_epi16(_mm256_sub_epi16(l,c)),_mm256_abs_epi16(_mm256_sub_epi16(r,c))),_mm256_add_epi16(_mm256_abs_epi16(_mm256_sub_epi16(u,c)),_mm256_abs_epi16(_mm256_sub_epi16(v,c))));
            const auto res=_mm256_sub_epi16(_mm256_slli_epi16(c,2),_mm256_add_epi16(_mm256_add_epi16(l,r),_mm256_add_epi16(u,v)));
            const auto lum=_mm256_and_si256(_mm256_cmpgt_epi16(c,_mm256_set1_epi16(23)),_mm256_cmpgt_epi16(_mm256_set1_epi16(232),c));
            const auto extreme=_mm256_or_si256(_mm256_cmpgt_epi16(_mm256_set1_epi16(64),c),_mm256_cmpgt_epi16(c,_mm256_set1_epi16(192)));
            const auto maxA=_mm256_blendv_epi8(_mm256_set1_epi16(37),_mm256_set1_epi16(49),extreme);
            auto enhance=_mm256_and_si256(lum,_mm256_and_si256(_mm256_cmpgt_epi16(g,_mm256_set1_epi16(5)),_mm256_cmpgt_epi16(_mm256_set1_epi16(32),g)));
            enhance=_mm256_and_si256(enhance,_mm256_and_si256(_mm256_cmpgt_epi16(maxA,activity),_mm256_cmpgt_epi16(_mm256_add_epi16(_mm256_slli_epi16(g,1),_mm256_set1_epi16(1)),activity)));
            enhance=_mm256_and_si256(enhance,_mm256_cmpgt_epi16(_mm256_abs_epi16(res),_mm256_set1_epi16(threshold-1)));
            const auto sign=_mm256_blendv_epi8(_mm256_set1_epi16(-1),_mm256_set1_epi16(1),_mm256_cmpgt_epi16(res,_mm256_setzero_si256()));
            auto delta=_mm256_and_si256(enhance,sign);
            if(balance) {
                const auto peak=_mm256_and_si256(_mm256_and_si256(_mm256_cmpgt_epi16(c,l),_mm256_cmpgt_epi16(c,r)),_mm256_and_si256(_mm256_cmpgt_epi16(c,u),_mm256_cmpgt_epi16(c,v)));
                const auto valley=_mm256_and_si256(_mm256_and_si256(_mm256_cmpgt_epi16(l,c),_mm256_cmpgt_epi16(r,c)),_mm256_and_si256(_mm256_cmpgt_epi16(u,c),_mm256_cmpgt_epi16(v,c)));
                auto noise=_mm256_and_si256(lum,_mm256_and_si256(_mm256_cmpgt_epi16(_mm256_set1_epi16(5),g),_mm256_or_si256(peak,valley)));
                noise=_mm256_and_si256(noise,_mm256_and_si256(_mm256_cmpgt_epi16(activity,_mm256_set1_epi16(7)),_mm256_cmpgt_epi16(_mm256_set1_epi16(21),activity)));
                noise=_mm256_andnot_si256(enhance,_mm256_and_si256(noise,_mm256_cmpgt_epi16(_mm256_abs_epi16(res),_mm256_set1_epi16(11))));
                delta=_mm256_add_epi16(delta,_mm256_and_si256(noise,_mm256_sub_epi16(_mm256_setzero_si256(),sign)));
            }
            const auto result=_mm256_add_epi16(c,delta);
            _mm_storeu_si128(reinterpret_cast<__m128i*>(d+p),_mm_packus_epi16(_mm256_castsi256_si128(result),_mm256_extracti128_si256(result,1)));
        }
        for(;x<w-1;++x) {
            const std::size_t p=std::size_t(y)*w+x;const int c=s[p],l=s[p-1],r=s[p+1],u=s[p-w],v=s[p+w];
            if(c<24||c>231)continue;
            const int g=std::abs(l-r)+std::abs(u-v),a=std::abs(l-c)+std::abs(r-c)+std::abs(u-c)+std::abs(v-c),res=4*c-l-r-u-v;
            const int maxA=(c<64||c>192)?48:36;
            int delta=0;
            if(g>=6&&g<32&&a<=maxA&&2*g>=a&&std::abs(res)>=threshold)delta=res>0?1:-1;
            else if(balance&&g<=4&&a>=8&&a<=20&&std::abs(res)>=12&&((c>l&&c>r&&c>u&&c>v)||(c<l&&c<r&&c<u&&c<v)))delta=res>0?-1:1;
            d[p]=uint8_t(c+delta);
        }
    }
}
__attribute__((target("avx2")))
void sharpPlane(const uint8_t* s,uint8_t* d,int w,int h,int edge,int blend) {
    const int threshold=std::max(8,(32+blend-1)/blend);
    // Signed-round then clamp to +/-1 is exactly a threshold/sign decision.
#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(4)
#endif
    for(int y=1;y<h-1;++y) {
        int x=1;
        for(;x+15<w-1;x+=16) {
            const std::size_t p=std::size_t(y)*w+x;
            const auto c=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(s+p)));
            const auto l=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(s+p-1)));
            const auto r=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(s+p+1)));
            const auto u=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(s+p-w)));
            const auto v=_mm256_cvtepu8_epi16(_mm_loadu_si128(reinterpret_cast<const __m128i*>(s+p+w)));
            const auto g=_mm256_add_epi16(_mm256_abs_epi16(_mm256_sub_epi16(l,r)),_mm256_abs_epi16(_mm256_sub_epi16(u,v)));
            const auto res=_mm256_sub_epi16(_mm256_slli_epi16(c,2),_mm256_add_epi16(_mm256_add_epi16(l,r),_mm256_add_epi16(u,v)));
            const auto eligible=_mm256_and_si256(_mm256_and_si256(_mm256_cmpgt_epi16(g,_mm256_set1_epi16(3)),_mm256_cmpgt_epi16(_mm256_set1_epi16(edge),g)),_mm256_cmpgt_epi16(_mm256_abs_epi16(res),_mm256_set1_epi16(threshold-1)));
            const auto sign=_mm256_blendv_epi8(_mm256_set1_epi16(-1),_mm256_set1_epi16(1),_mm256_cmpgt_epi16(res,_mm256_setzero_si256()));
            const auto result=_mm256_add_epi16(c,_mm256_and_si256(eligible,sign));
            const auto packed=_mm_packus_epi16(_mm256_castsi256_si128(result),_mm256_extracti128_si256(result,1));
            _mm_storeu_si128(reinterpret_cast<__m128i*>(d+p),packed);
        }
        for(;x<w-1;++x) {
            const std::size_t p=std::size_t(y)*w+x;const int c=s[p];
            const int g=std::abs(int(s[p-1])-int(s[p+1]))+std::abs(int(s[p-w])-int(s[p+w]));
            const int res=4*c-s[p-1]-s[p+1]-s[p-w]-s[p+w];
            if(g>=4&&g<edge&&std::abs(res)>=threshold)d[p]=uint8_t(std::clamp(c+(res>0?1:-1),0,255));
        }
    }
}
#endif
void plane(const uint8_t* s, uint8_t* d, int w, int h, int range, int edge, bool sharp, int blend) {
#ifdef USE_RUNTIME_AVX2
    static const bool avx2=__builtin_cpu_supports("avx2");
    if(sharp&&avx2&&blend>0) {sharpPlane(s,d,w,h,edge,blend);return;}
#endif
    // Each row writes independent output; reduction-free, bit-exact parallelism.
#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(4)
#endif
    for (int y=1; y<h-1; ++y) for (int x=1; x<w-1; ++x) {
        const std::size_t p = std::size_t(y)*w+x;
        const int c=s[p];
        const int g=std::abs(int(s[p-1])-int(s[p+1]))+std::abs(int(s[p-w])-int(s[p+w]));
        if (g>=edge) continue;
        int correction=0;
        if (sharp) {
            // Cross low-pass residual; avoid enhancing flat noise and strong contours.
            int residual=4*c-s[p-1]-s[p+1]-s[p-w]-s[p+w];
            if (std::abs(residual)<8 || g<4) continue;
            correction=std::clamp(signedRound(residual*blend,64),-1,1);
        } else {
            int sum=4*c, weight=4;
            for(int dy=-1;dy<=1;++dy) for(int dx=-1;dx<=1;++dx) {
                if(!dx&&!dy) continue;
                const int v=s[std::size_t(int(y)+dy)*w+x+dx];
                if(std::abs(v-c)<=range) {sum+=v; ++weight;}
            }
            // Blend before rounding, to keep weak corrections unbiased.
            correction=signedRound((sum-weight*c)*blend,weight*16);
            if(mode=="legacy"&&blend==16) correction=(sum+weight/2)/weight-c;
            if(mode!="legacy") correction=std::clamp(correction,-1,1);
        }
        d[p]=uint8_t(std::clamp(c+correction,0,255));
    }
}
int number(const char* s) {
    std::size_t n=0; int v=std::stoi(s,&n);
    if(n!=std::strlen(s)) throw std::invalid_argument("Invalid integer");
    return v;
}
}
void configurePreprocess(const char* name,int a) {
    const std::string m(name);
    if(m!="identity"&&m!="smooth"&&m!="chroma"&&m!="sharp"&&m!="legacy"&&m!="hybrid"&&m!="perceptual"&&m!="balanced"&&m!="adaptive")
        throw std::invalid_argument("Unknown profile");
    if(a<0||a>16) throw std::invalid_argument("Amount must be 0..16");
    mode=m; amount=a;
}
void processYUVFrame(const uint8_t* src,uint8_t* dst,int w,int h,int crf) {
    if(!src||!dst||w<=0||h<=0||(w&1)||(h&1)) throw std::invalid_argument("Invalid YUV420P frame");
    const std::size_t n=std::size_t(w)*h;
    if(mode=="identity"||!amount) {std::memmove(dst,src,n+n/2);return;}
    // Support in-place callers without read-after-write changes.
    std::vector<uint8_t> backup;
    if(src==dst) {backup.assign(src,src+n+n/2);src=backup.data();}
    std::memcpy(dst,src,n+n/2);
    const int q=std::clamp(crf,0,51), r=3+q/6, e=18+q/2;
    if(mode=="adaptive") {
#ifdef USE_RUNTIME_AVX2
        if(__builtin_cpu_supports("avx2"))perceptualPlaneAVX2(src,dst,w,h,q,true);
        else
#endif
        perceptualPlane(src,dst,w,h,q,true);
        // Workspace only, not temporal state. Independent across calling threads.
        thread_local std::vector<uint8_t> weak;
        weak.assign(src,src+n);
        plane(src,weak.data(),w,h,r,e,true,1);
        for(std::size_t p=0;p<n;++p)if(src[p]<24||src[p]>231)weak[p]=src[p];
        // Dense texture: preserve original weak enhancement rather than suppress
        // genuine grain/detail. 16x16 tile decisions use input features only.
        for(int by=0;by<h;by+=16)for(int bx=0;bx<w;bx+=16) {
            const int ey=std::min(by+16,h),ex=std::min(bx+16,w);
            int total=0,strong=0,count=0;
            for(int y=std::max(by,1);y<std::min(ey,h-1);y+=2)
                for(int x=std::max(bx,1);x<std::min(ex,w-1);x+=2) {
                    const std::size_t p=std::size_t(y)*w+x;
                    const int g=std::abs(int(src[p-1])-int(src[p+1]))+std::abs(int(src[p-w])-int(src[p+w]));
                    total+=g;strong+=g>=32;++count;
                }
            if(count&&(total>=12*count||strong*4>=count))
                for(int y=by;y<ey;++y)std::copy(weak.data()+std::size_t(y)*w+bx,weak.data()+std::size_t(y)*w+ex,dst+std::size_t(y)*w+bx);
        }
        return;
    }
    if(mode=="perceptual"||mode=="balanced") {
#ifdef USE_RUNTIME_AVX2
        if(__builtin_cpu_supports("avx2")) {perceptualPlaneAVX2(src,dst,w,h,q,mode=="balanced");return;}
#endif
        perceptualPlane(src,dst,w,h,q,mode=="balanced");return;
    }
    if(mode!="chroma") plane(src,dst,w,h,r,e,mode=="sharp"||mode=="hybrid",amount);
    if(mode!="sharp") {
        const int chromaBlend=mode=="hybrid"?16:amount;
        plane(src+n,dst+n,w/2,h/2,r+3,e+8,false,chromaBlend);
        plane(src+n+n/4,dst+n+n/4,w/2,h/2,r+3,e+8,false,chromaBlend);
    }
}
#ifndef PREPROCESS_LIBRARY
int main(int argc,char** argv) {
    try {
        if(argc<8||argc>9) throw std::invalid_argument("Usage: preprocess input.yuv output.yuv width height crf mode amount [frames]");
        const int w=number(argv[3]),h=number(argv[4]),q=number(argv[5]);
        const int limit=argc==9?number(argv[8]):0;
        if(w<=0||h<=0||(w&1)||(h&1)||q<0||q>51||limit<0) throw std::invalid_argument("Invalid dimensions/CRF/frame limit");
        char a[MAX_PATH],b[MAX_PATH];
        const DWORD na=GetFullPathNameA(argv[1],MAX_PATH,a,nullptr),nb=GetFullPathNameA(argv[2],MAX_PATH,b,nullptr);
        if(!na||!nb||na>=MAX_PATH||nb>=MAX_PATH) throw std::invalid_argument("Invalid/overlong path");
        if(_stricmp(a,b)==0) throw std::invalid_argument("Input/output must differ");
        HANDLE hi=CreateFileA(a,0,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_EXISTING,0,nullptr);
        HANDLE ho=CreateFileA(b,0,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_EXISTING,0,nullptr);
        BY_HANDLE_FILE_INFORMATION fi{},fo{};
        bool same=hi!=INVALID_HANDLE_VALUE&&ho!=INVALID_HANDLE_VALUE&&GetFileInformationByHandle(hi,&fi)&&GetFileInformationByHandle(ho,&fo)&&fi.dwVolumeSerialNumber==fo.dwVolumeSerialNumber&&fi.nFileIndexHigh==fo.nFileIndexHigh&&fi.nFileIndexLow==fo.nFileIndexLow;
        if(hi!=INVALID_HANDLE_VALUE)CloseHandle(hi);if(ho!=INVALID_HANDLE_VALUE)CloseHandle(ho);
        if(same) throw std::invalid_argument("Input/output refer to the same file");
        configurePreprocess(argv[6],number(argv[7]));
        const std::size_t n=std::size_t(w)*h*3/2;
        std::ifstream in(argv[1],std::ios::binary|std::ios::ate);
        if(!in||in.tellg()<=0||std::size_t(in.tellg())%n) throw std::invalid_argument("Missing/empty/incomplete source frame");
        if(limit&&std::size_t(in.tellg())/n<std::size_t(limit))throw std::invalid_argument("Insufficient input frames");
        in.seekg(0);std::ofstream out(argv[2],std::ios::binary);
        if(!in||!out) throw std::runtime_error("Cannot open input/output");
        std::vector<uint8_t> s(n),d(n);int frames=0;double compute=0;
        const auto start=std::chrono::steady_clock::now();
        while((!limit||frames<limit)&&in.read(reinterpret_cast<char*>(s.data()),n)) {
            auto t=std::chrono::steady_clock::now(); processYUVFrame(s.data(),d.data(),w,h,q);
            compute+=std::chrono::duration<double>(std::chrono::steady_clock::now()-t).count();
            out.write(reinterpret_cast<char*>(d.data()),n);if(!out)throw std::runtime_error("Write failed");++frames;
        }
        out.flush();if(!out||!frames||(limit&&frames!=limit)) throw std::runtime_error("Write failure / insufficient input frames");
        const double total=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::cout<<"{\"frames\":"<<frames<<",\"compute_seconds\":"<<compute<<",\"wall_seconds\":"<<total<<"}\n";
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
#endif
