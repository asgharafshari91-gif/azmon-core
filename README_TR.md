# AZMON 0.3.0 — Ana ağ kaynak yayını

Bu paket AZMON ana ağı için ayrı genesis ve CPU başlangıç zorluğu içerir. Paket hazırlamak, halka açık ağı başlatmak değildir. Dağıtım durumu **MAINNET_PRELAUNCH_VALIDATION**: yeni sürüm VPS ve Mac üzerinde doğrulanmalı; ana ağ kimlik doğrulama/cihaz kayıtları, TLS madencilik uç noktası ve web Explorer bağlantısı tamamlanmalıdır. Canlı site bu adımlar tamamlanana kadar açılmış ana ağ gibi gösterilmemelidir.

## Sabit kurallar

| Kural | Değer |
|---|---|
| Algoritma | SHA-256d |
| Arz sınırı | 105.000.000 AZMON |
| İlk blok ödülü | 250 AZMON |
| Hassasiyet | 8 ondalık |
| Yarılanma | 210.000 blok |
| Ödül olgunlaşması | 100 blok |
| Hedef blok aralığı | Ortalama 600 saniye |
| Zorluk ayarı | 2.016 blokta; dört kat sınırı |
| Başlangıç bits | `1d05e0a5` |
| Başlangıç zorluğu | Yaklaşık 0,1701372573 |
| Genesis ödülü | 0; OP_RETURN, harcanamaz |
| Kurucuya ayrılmış ön kazım | 0 |
| Adres biçimi | `az1…` |
| P2P / yerel RPC | 29755 / 29754 |
| Ağ mesaj kimliği | `a75a4d4e` |
| Zincir veri alt klasörü | `azmon-mainnet` |

Sıfırıncı yükseklikte ödül verilmemesi ve tam sayı yuvarlaması nedeniyle 1. bloktan itibaren kuramsal azami ihraç **104.999.749,96850000 AZMON** olur. Daha düşük talep edilen ödüller ve kaybolan anahtarlar harcanabilir arzı azaltabilir.

Genesis: `000000057eacbad83bbf08d90a98403e0bcfc5bd8566fb9d92962786096d274c`.
Genesis ayrıntıları, başlığı ve ham işlemi `genesis.json` içindedir. `scripts/check_release.py` bunları JSON etiketine güvenmeden yeniden hash eder, hedefi ve sıfır ödülü denetler.

Başlangıç hedefi bir Mac'in 30 saniyelik ham SHA-256d ölçümündeki 1.217.906 H/s değerine göre hesaplandı. Gerçek madenci yazılımı, ağ gecikmesi ve ek cihazlar süreyi değiştirir; her blok 10 dakika sürmez. SHA-256d, ASIC cihazlarını dışlamaz. Bu küçük başlangıç hash gücü Bitcoin düzeyinde güvenlik sağlamaz. Ani hash artışı ve ardından çıkış, 2.016 blokluk ayar döneminde blokları yavaşlatabilir.

## Kaynak ve bakım tabanı

Bitcoin Core **30.4** kaynakları üzerine AZMON değişiklikleri uygulanmıştır. Üst kaynak arşivi resmi HTTPS yayınının SHA256SUMS dosyasına karşı doğrulanmıştır. Detaylar `UPSTREAM.json`; yeniden uygulanabilir değişiklikler `azmon.patch` içindedir. Yayıncı PGP imzası bu ortamda bağımsız doğrulanmadı. AZMON paket sürümü 0.3.0, çekirdek yazılımının üst kaynak sürüm numarası 30.4.0'dır.

Eski testnet ve RC1 bakiyeleri taşınmaz. RC1'in `az1…` adres biçimi aynı olsa da zincirler farklıdır; yeni ana ağ için ayrı cüzdan ve cihaz anahtarı oluşturun. Eski veri klasörlerini bu sürüme vermeyin.

## VPS: derleme

Ubuntu 24.04 için gerekli derleme araçları ve kütüphaneler: CMake, C++ derleyici, pkg-config, Boost, libevent, SQLite geliştirme paketleri. Önceki VPS kurulumunda bu araçlar kurulmuştu.

Yeni klasör kullanın; `/opt/azmon-rc1` üzerine yazmayın:

```bash
cd /opt
unzip -q AZMON-Mainnet-0.3.0.zip
mv AZMON-Mainnet-0.3.0 azmon-mainnet
cd /opt/azmon-mainnet
sha256sum -c SHA256SUMS
AZMON_JOBS=1 bash scripts/build.sh > build-mainnet.log 2>&1
python3 scripts/check_release.py
```

Klasör zaten varsa önce sürümü inceleyin; `mv` veya çıkarma komutlarını yeniden çalıştırmayın. Bu adımlar servisleri veya canlı siteyi değiştirmez.

## Yerel doğrulamalar

```bash
python3 scripts/check_consensus.py
python3 scripts/check_retarget.py
python3 scripts/check_transition.py
python3 scripts/test_worker_auth.py
python3 scripts/test_client_io.py
setsid --wait python3 scripts/test_chain.py --build build </dev/null
```

`setsid` Linux içindir. Son test iki gerçek ana ağ düğümünü geçici veri klasörlerinde başlatır, başlangıç zorluğunda bir blok üretir, ödeme adresi/ödülü ve yeniden başlamayı kontrol eder; yerel CPU istemcisini 70 saniye çalıştırır. Yardımcı nonce hesabı birkaç dakika sürebilir. Geçici bloklar yayınlanmaz ve üretim verisine kopyalanmaz. Bu test yeni zorlukta tam 2.016 blok, 100 blok olgunlaşması veya bakiyeli transfer testi değildir. Önceki RC1 üzerinde yapılan bu kontroller yeni sürüm sonucu olarak sunulmaz. Raporlar `reports/` altında kapsamlarıyla birlikte yer alır.

## İzole servis hazırlığı

```bash
sudo bash ops/install-node.sh --prepare
sudo bash ops/configure-mining.sh
```

İlk komut `/usr/local/lib/azmon-mainnet` ikililerini, `azmonmain` sistem kullanıcısını ve ayrı veri klasörlerini kullanır. Mevcut bir ana ağ ayar dosyasının üzerine otomatik yazmaz. P2P başlangıçta loopback'tedir; RPC daima yereldir. RC1/testnet servislerini, DNS'i veya güvenlik duvarını değiştirmez.

İkinci komut `azmon-wallet` cüzdanı, yeni `az1` ödül adresi ve yerel anahtarı hashlenmiş cihaz kaydı oluşturur. Anahtar bir kez ekranda gösterilir; sohbetlere göndermeyin. Stratum 127.0.0.1:3373, Explorer 127.0.0.1:29980 üzerinde hazırlanır. Bu yerel cihaz kaydı henüz web sitesindeki Supabase ana ağ kaydıyla entegre değildir.

Servisler: `azmon-mainnet-node`, `azmon-mainnet-peer`, `azmon-mainnet-stratum`, `azmon-mainnet-explorer`.
Veriler: `/var/lib/azmon-mainnet`, `/var/lib/azmon-mainnet-peer`.
İkinci düğümün RPC/P2P portları: 29764 / 29765.

Halka açık madencilik başlamadan önce kaynak ve açılış duyurusu yayımlanmalı; üretim zincirinde kurucuya özel blok kazılmamalıdır. Public TLS Stratum bağlantısı ve ana ağ web kayıtları ayrı dağıtım adımlarıdır. Bu paketin kurulması bunları olmuş saymaz.

## CPU istemcisi

```bash
python3 stratum/cpu_miner.py --host 127.0.0.1 --port 3373 --seconds 120
```

İstemci cihaz kimliğini ve anahtarını etkileşimli alır. Gerçek ölçülen hash hızını oturum sonunda yazar. Yüksek başlangıç zorluğunda 120 saniyede blok bulunmaması normaldir. Düzenli heartbeat mesajları bağlantıyı canlı tutar; sunucu yetkilendirilmemiş bağlantılara 30 saniye tanır. Yetkilendirilmiş istemcilerin cihaz kaydı yeni işler gönderilirken yeniden doğrulanır. İnternete açık bağlantı TLS gerektirir; düz metin bağlantıyı internete açmayın.

Deneysel SOLO servisinde sabit ağ zorluğu ve 32 eşzamanlı bağlantı sınırı vardır. VarDiff, version rolling, PPS/PPLNS paylaşımı, ASIC firmware uyumluluğu, büyük ölçek/yük ve DDoS dayanımı doğrulanmadı. Her kabul edilen blok adayının ödülü işlem ücretleriyle birlikte cihazın kayıtlı adresine gider; ayrı bir web havuz bakiyesi tutulmaz. Bir cihaz kaydetmek kazımı başlatmaz.

## Cüzdan güvenliği ve kalan kapsam

Özel anahtarlar yerel AZMON Core cüzdanındadır. `scripts/wallet_tool.py` doğru genesis'i denetleyerek adres, bakiye, şifreleme ve `backupwallet` işlemlerine yardımcı olur; anahtar veya parola komut satırı argümanına yazılmaz. Yedek özel anahtar içerir, web köküne konmaz. Soğuk saklama için yedeği güvenli çevrimdışı ortamda korumak ve geri yüklemeyi sınamak gerekir. Bunun Ledger/Trezor gibi donanım cüzdanlarında AZMON desteği anlamına geldiği iddia edilmez.

Bu sürüm bağımsız güvenlik denetiminden veya tam upstream regresyon paketinden geçmedi. Linux yerel sonuçları Mac/VPS dağıtım sonucu yerine geçmez. Borsa listelenmesi, piyasa fiyatı veya getiri sözü verilmez. Yeni ana ağ doğrulanıp devreye alınana kadar canlı site gerçek mevcut ağı göstermeye devam etmelidir.
