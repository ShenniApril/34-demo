#include "preprocess.h"
#include <cassert>
#include <vector>
int main() {
    std::vector<uint8_t> src(16*16*3/2),dst(src.size());
    for(unsigned i=0;i<src.size();++i)src[i]=uint8_t(i*7);
    for(const char* m:{"identity","smooth","chroma","sharp","legacy","hybrid","perceptual","balanced","adaptive","context","content","guarded"}) {
        configurePreprocess(m,4);processYUVFrame(src.data(),dst.data(),16,16,28);
        auto alias=src;processYUVFrame(alias.data(),alias.data(),16,16,28);assert(alias==dst);
    }
    bool threw=false;try{processYUVFrame(src.data(),dst.data(),15,16,28);}catch(...){threw=true;}
    assert(threw);
    std::vector<uint8_t> hd(1920*1080*3/2),separate(hd.size());
    for(unsigned i=0;i<hd.size();++i)hd[i]=uint8_t(i*7);
    configurePreprocess("guarded",2);
    processYUVFrame(hd.data(),separate.data(),1920,1080,28);
    auto inplace=hd;processYUVFrame(inplace.data(),inplace.data(),1920,1080,28);
    assert(inplace==separate);
    assert(std::equal(hd.begin(),hd.begin()+1920*1080,separate.begin()));
}
