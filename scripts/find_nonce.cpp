// Genesis/validation helper, not an ASIC or production pool miner.
#include <crypto/sha256.h>
#include <array>
#include <atomic>
#include <cstdint>
#include <iostream>
#include <string>
#include <thread>
#include <vector>
static unsigned char nibble(char c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;throw 1;}
int main(int argc,char** argv){
 if(argc!=3)return 2;std::string hex=argv[1],target=argv[2];if(hex.size()!=152||target.size()!=64)return 2;
 std::array<unsigned char,76> prefix{};std::array<unsigned char,32> limit{};
 for(int i=0;i<76;++i)prefix[i]=nibble(hex[2*i])*16+nibble(hex[2*i+1]);
 for(int i=0;i<32;++i)limit[31-i]=nibble(target[2*i])*16+nibble(target[2*i+1]);
 SHA256AutoDetect();CSHA256 mid;mid.Write(prefix.data(),64);
 std::atomic<bool> found{false};uint32_t answer=0;
 const unsigned workers=4;std::vector<std::thread> threads;
 for(unsigned id=0;id<workers;++id)threads.emplace_back([&,id]{
  std::array<unsigned char,16> tail{};for(int i=0;i<12;++i)tail[i]=prefix[64+i];
  for(uint64_t n=id;n<=UINT32_MAX&&!found.load(std::memory_order_relaxed);n+=workers){
   for(int i=0;i<4;++i)tail[12+i]=n>>(8*i);
   unsigned char first[32],out[32];CSHA256 state=mid;state.Write(tail.data(),16).Finalize(first);CSHA256().Write(first,32).Finalize(out);
   bool smaller=false,equal=true;for(int i=31;i>=0;--i){if(out[i]<limit[i]){smaller=true;equal=false;break;}if(out[i]>limit[i]){equal=false;break;}}
   if(smaller||equal){bool expected=false;if(found.compare_exchange_strong(expected,true))answer=n;break;}
  }
 });
 for(auto& thread:threads)thread.join();if(!found)return 1;std::cout<<answer<<'\n';return 0;
}
