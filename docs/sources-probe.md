# LobangLeh source probe

Measured 2026-10-03 from a residential Singapore IP (Windows, Python 3.9 urllib + feedparser). CI (GitHub Actions) IPs are **not yet verified**; rerun `python tools/probe_sources.py` in a workflow before trusting this.

Columns: status = HTTP status with the Chrome-style UA; items = parsed items (telegram = `tgme_widget_message_text` blocks on the t.me/s page); F&B = items out of the newest ~20 (telegram: newest 12) matching a loose F&B keyword regex, so relative only; newest = newest item date; UA = `library` (plain Python-urllib works), `browser` (needs a Chrome UA), `-` (neither). Library-UA status in parentheses when it differs from browser.

Key finding: **the plain library UA is 403'd by most WordPress sites** (Eatbook, Seth Lui, Great Deals, Little Big Red Dot, Honeycombers, Vulcan Post ...), so the collector must send a browser-like UA. Google News, Telegram, SingPromos, TheSmartLocal, Straits Times, CNA, Lady Iron Chef, Ranting Panda, Confirm Good answer to either.

## All candidates

| name | type | url | status | items | F&B | newest | UA | verdict |
|---|---|---|---|---|---|---|---|---|
| singpromos | rss | https://singpromos.com/feed/ | 200 | 15 | 9 | 2026-10-03 | library | KEPT as `singpromos` |
| singpromos_fnb | rss | https://singpromos.com/category/food-beverage/feed/ | 200 | 0 | 0 | - | - | 200 but 0 items (wrong slug) |
| greatdeals | rss | https://www.greatdeals.com.sg/feed/ | 200 (lib 403) | 10 | 8 | 2026-10-02 | browser | alive, but main feed mixes in non-F&B (trolley keychains, TECNO ovens); category/tag feeds kept instead |
| greatdeals_dining | rss | https://www.greatdeals.com.sg/category/dining/feed/ | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |
| littlebigreddot | rss | https://littlebigreddot.com/feed/ | 200 (lib 403) | 10 | 6 | 2026-10-03 | browser | alive but general city news (6/10); lbr_food category kept instead |
| thesmartlocal | rss | https://thesmartlocal.com/feed/ | 200 | 10 | 2 | 2026-10-02 | library | KEPT as `thesmartlocal` |
| thesmartlocal_food | rss | https://thesmartlocal.com/read/category/food/feed/ | 200 | 0 | 0 | - | - | 200 but 0 items |
| eatbook | rss | https://eatbook.sg/feed/ | 200 (lib 403) | 10 | 9 | 2026-10-02 | browser | KEPT as `eatbook` |
| eatbook_deals_v1 | rss | https://eatbook.sg/category/food-news/feed/ | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 (wrong slug) |
| eatbook_promos | rss | https://eatbook.sg/tag/promotions/feed/ | 200 (lib 403) | 1 | 1 | 2020-03-24 | browser | stale (2020-03-24) |
| sethlui | rss | https://sethlui.com/feed/ | 200 (lib 403) | 10 | 7 | 2026-10-03 | browser | alive 7/10; sethlui_food (Food category) kept instead because the main feed carries JB salons etc. |
| sethlui_deals | rss | https://sethlui.com/category/singapore-food-news/feed/ | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |
| sethlui_promos | rss | https://sethlui.com/tag/promotions/feed/ | 200 (lib 403) | 10 | 5 | 2026-07-13 | browser | stale (2026-07-13) |
| danielfooddiary | rss | https://danielfooddiary.com/feed/ | 403 (lib 500) | 0 | 0 | - | - | BLOCKED 403 (WordPress/Cloudflare-style wall on /feed from both UAs); use the t.me/s/danielfooddiary channel instead |
| misstamchiak | rss | https://www.misstamchiak.com/feed/ | 404 | 0 | 0 | - | - | DEAD 404 (feed path unknown/removed) |
| mothership | rss | https://mothership.sg/feed/ | 200 (lib 403) | 10 | 3 | 2026-10-03 | browser | alive but ~3/10 F&B, general news; not kept (use gnews / tg media instead) |
| mothership_food | rss | https://mothership.sg/category/food/feed/ | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |
| timeout_sg | rss | https://www.timeout.com/singapore/feed | 404 | 0 | 0 | - | - | DEAD 404 |
| timeout_sg_rss | rss | https://www.timeout.com/singapore/rss | 404 | 0 | 0 | - | - | DEAD 404 |
| honeycombers | rss | https://thehoneycombers.com/singapore/feed/ | 200 (lib 403) | 10 | 5 | 2026-10-02 | browser | KEPT as `honeycombers` |
| lifestyleasia_sg | rss | https://www.lifestyleasia.com/sg/feed/ | 202 (lib 403) | 0 | 0 | - | - | BLOCKED 202 empty body (bot challenge) |
| lifestyleasia_food | rss | https://www.lifestyleasia.com/sg/food-drink/feed/ | 202 (lib 403) | 0 | 0 | - | - | BLOCKED 202 empty body |
| hungrygowhere | rss | https://hungrygowhere.com/feed/ | 500 | 0 | 0 | - | - | DEAD 500 |
| burpple_blog | rss | https://blog.burpple.com/feed/ | 404 | 0 | 0 | - | - | DEAD 404 |
| 8days | rss | https://www.8days.sg/rss.xml | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |
| st_life | rss | https://www.straitstimes.com/news/life/rss.xml | 200 | 39 | 8 | 2026-10-03 | library | KEPT as `straitstimes_life` |
| st_singapore | rss | https://www.straitstimes.com/news/singapore/rss.xml | 200 | 39 | 2 | 2026-10-03 | library | alive, general news 2/39 F&B; not kept (st_life kept instead) |
| cna_sg | rss | https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=10416 | 200 | 20 | 3 | 2026-10-03 | library | alive, general news 3/20; not kept |
| cna_lifestyle | rss | https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511 | 200 | 18 | 7 | 2026-10-03 | library | KEPT as `cna_lifestyle` |
| asiaone | rss | https://www.asiaone.com/rss.xml | 404 | 0 | 0 | - | - | DEAD 404 |
| todayonline | rss | https://www.todayonline.com/feed | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 (library UA 403) |
| dollarsandsense | rss | https://dollarsandsense.sg/feed/ | 200 | 10 | 0 | 2026-10-03 | library | alive, 0 F&B |
| vulcanpost | rss | https://vulcanpost.com/feed/ | 200 (lib 403) | 10 | 4 | 2026-10-02 | browser | alive, business news, 4/10 F&B; not kept |
| mustsharenews | rss | https://mustsharenews.com/feed/ | 200 (lib 403) | 10 | 1 | 2026-10-03 | browser | alive, 1/10 F&B; not kept |
| goodyfeed | rss | https://goodyfeed.com/feed/ | 200 (lib 403) | 10 | 3 | 2026-10-02 | browser | alive, 3/10 F&B; not kept |
| ladyironchef | rss | https://www.ladyironchef.com/feed/ | 200 | 20 | 15 | 2026-09-29 | library | KEPT as `ladyironchef` |
| ieatishootipost | rss | https://ieatishootipost.sg/feed/ | 200 (lib 403) | 12 | 8 | 2026-09-22 | browser | alive, but long-form reviews (newest 2026-09-22), no deals/opening signal; not kept |
| alvinology | rss | https://www.alvinology.com/feed/ | 200 (lib 403) | 30 | 3 | 2026-10-03 | browser | alive but 3/30 F&B (events/tech); not kept |
| sgmagazine | rss | https://sgmagazine.com/feed/ | 200 (lib 403) | 10 | 1 | 2024-12-31 | browser | stale (2024-12-31) |
| seedly | rss | https://blog.seedly.sg/feed/ | 200 (lib 403) | 100 | 0 | 2026-09-23 | browser | alive, 0 F&B, finance; 2.7 MB |
| moneysmart | rss | https://blog.moneysmart.sg/feed/ | 200 (lib 403) | 25 | 2 | 2026-10-01 | browser | alive, finance, 2/25 F&B |
| singsaver | rss | https://www.singsaver.com.sg/blog/feed | 404 | 0 | 0 | - | - | DEAD 404 |
| yahoo_sg | rss | https://sg.news.yahoo.com/rss/ | 200 (lib 429) | 5 | 0 | 2026-09-24 | browser | alive, 5 items, 0 F&B; not kept |
| theindependent_sg | rss | https://theindependent.sg/feed/ | 200 | 50 | 7 | 2026-10-03 | library | alive, general news, 7/50 F&B; not kept |
| theedgesg | rss | https://www.theedgesingapore.com/rss.xml | 200 (lib 403) | 10 | 3 | 2026-10-03 | browser | alive, business, 3/10; not kept |
| businesstimes_life | rss | https://www.businesstimes.com.sg/rss/life-culture | 200 | 16 | 3 | 2022-11-19 | library | stale (2022-11-19) |
| beautifulfood_sg | rss | https://thebeautyfoodie.com/feed/ | 200 (lib 403) | 10 | 4 | 2026-09-24 | browser | alive, 4/10, last 2026-09-24; not kept |
| foodadvisor | rss | https://www.foodadvisor.com.sg/feed/ | 403 CF | 0 | 0 | - | - | BLOCKED Cloudflare challenge (403 + cf- headers) |
| femalemag | rss | https://www.female.com.sg/feed/ | 0 | 0 | 0 | - | - | DEAD connection error |
| thefinance_sg | rss | https://thefinance.sg/feed/ | 200 | 20 | 4 | 2026-10-03 | library | alive, finance 4/20; not kept |
| kopitiam_blog | rss | https://www.thesmartlocal.com/read/food-news/feed/ | 404 | 0 | 0 | - | - | DEAD 404 |
| tg_sgfooddeals | telegram | https://t.me/s/sgfooddeals | 200 | 20 | 11 | 2026-10-02 | library | KEPT as `tg_sgfooddeals` |
| tg_sgkiasufoodies | telegram | https://t.me/s/sgkiasufoodies | 200 | 1 | 1 | 2025-10-04 | library | NOT the real channel: 1 message from 2025 (unrelated handle) |
| tg_kiasufoodies | telegram | https://t.me/s/kiasufoodies | 200 | 20 | 12 | 2026-10-03 | library | KEPT as `tg_kiasufoodies` |
| tg_sgfoodpromos | telegram | https://t.me/s/sgfoodpromos | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgdeals | telegram | https://t.me/s/sgdeals | 200 | 20 | 12 | 2024-04-28 | library | alive but stale (newest 2024-04-28) |
| tg_sgpromos | telegram | https://t.me/s/sgpromos | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_singaporefooddeals | telegram | https://t.me/s/singaporefooddeals | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgfoodlobang | telegram | https://t.me/s/sgfoodlobang | 200 | 4 | 3 | 2022-06-25 | library | alive but stale (2022) |
| tg_lobangsg | telegram | https://t.me/s/lobangsg | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sglobang | telegram | https://t.me/s/sglobang | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_kiasusg | telegram | https://t.me/s/kiasusg | 200 | 1 | 1 | 2025-03-13 | library | 1 stale message |
| tg_sgfoodies | telegram | https://t.me/s/sgfoodies | 200 | 15 | 10 | 2026-09-30 | library | KEPT as `tg_sgfoodies` |
| tg_sgcheapfood | telegram | https://t.me/s/sgcheapfood | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_foodsg | telegram | https://t.me/s/foodsg | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_burpple | telegram | https://t.me/s/burpple | 200 | 20 | 10 | 2026-09-08 | library | alive but newest 2026-09-08 and posts are Burpple Beyond membership ads; not kept |
| tg_sgfoodhunt | telegram | https://t.me/s/sgfoodhunt | 200 | 1 | 1 | 2024-02-11 | library | 1 stale message |
| tg_SGFoodDeals | telegram | https://t.me/s/SGFoodDeals | 200 | 20 | 11 | 2026-10-02 | library | case variant of sgfooddeals (identical page) |
| tg_SGKiasuFoodies | telegram | https://t.me/s/SGKiasuFoodies | 200 | 1 | 1 | 2025-10-04 | library | same page as tg_sgkiasufoodies |
| tg_mothershipsg | telegram | https://t.me/s/mothershipsg | 200 | 19 | 4 | 2026-10-03 | library | alive but general news, not F&B; not kept |
| tg_eatbooksg | telegram | https://t.me/s/eatbooksg | 200 | 17 | 12 | 2026-10-03 | library | alive and good, but duplicates eatbook RSS headlines; not kept (can be added as a faster channel for the same content) |
| gn_promo_1for1 | gnews | gnews: Singapore 1-for-1 deal | 200 | 66 | 13 (eye ~6/8) | 2026-10-03 | library | KEPT as `gnews_1for1` |
| gn_promo_fnb | gnews | gnews: Singapore food promotion discount | 200 | 41 | 17 (eye ~6/8) | 2026-10-02 | library | KEPT as `gnews_promo_fnb` |
| gn_first_outlet | gnews | gnews: "first outlet in Singapore" | 200 | 5 | 4 (eye 4/5) | 2026-09-30 | library | KEPT as `gnews_first_outlet` |
| gn_opens_sg | gnews | gnews: "opens in Singapore" restaurant OR cafe OR "bubble tea" | 200 | 9 | 4 (eye ~2/8 (hotels, MICE, film awards)) | 2026-10-02 | library | alive, but mostly hotels/MICE/film (~2/8 SG F&B); not kept |
| gn_flagship | gnews | gnews: "first Singapore outlet" OR "first store in Singapore" food | 200 | 2 | 2 (eye 2/2) | 2026-09-30 | library | KEPT as `gnews_flagship` |
| gn_overseas_brand | gnews | gnews: overseas chain debuts Singapore cafe restaurant opening | 200 | 4 | 4 (eye 4/4) | 2026-10-01 | library | KEPT as `gnews_overseas_brand` |
| gn_bubbletea | gnews | gnews: bubble tea brand Singapore new outlet | 200 | 15 | 12 (eye ~7/8) | 2026-10-02 | library | KEPT as `gnews_bubbletea` |
| gn_free_food | gnews | gnews: Singapore free food giveaway promotion | 200 | 13 | 8 (eye ~5/8) | 2026-10-02 | library | KEPT as `gnews_free_food` |
| gn_new_opening | gnews | gnews: new restaurant opening Singapore this week | 200 | 66 | 15 (eye 8/8) | 2026-10-03 | library | KEPT as `gnews_new_opening` |
| gn_sg_launch | gnews | gnews: "makes its Singapore debut" OR "arrives in Singapore" food OR drink | 200 | 1 | 1 (eye 0/1 (an Audi)) | 2026-10-02 | library | alive, 1 item (an Audi); not kept |
| gn_buy1get1 | gnews | gnews: Singapore buy 1 get 1 free drink OR burger OR pizza | 200 | 45 | 12 (eye ~5/8) | 2026-10-03 | library | KEPT as `gnews_buy1get1` |
| gn_chain_promo | gnews | gnews: McDonald's OR KFC OR Starbucks OR Koi OR LiHO Singapore promotion | 200 | 35 | 17 (eye ~6/8) | 2026-10-02 | library | KEPT as `gnews_chain_promo` |
| singpromos_dining | rss | https://singpromos.com/dining-restaurants-food/feed/ | 200 | 15 | 9 | 2026-10-03 | library | 200, byte-identical to the main feed (category slug ignored); not a distinct source |
| greatdeals_eatdrink | rss | https://www.greatdeals.com.sg/category/eat-drink/feed/ | 200 (lib 403) | 10 | 9 | 2026-10-02 | browser | KEPT as `greatdeals_eatdrink` |
| greatdeals_fooddeals | rss | https://www.greatdeals.com.sg/tag/food-deals/feed/ | 200 (lib 403) | 10 | 9 | 2026-10-02 | browser | alive, subset of greatdeals_eatdrink (2 F&B-deal tag); not kept as separate |
| greatdeals_storeopen | rss | https://www.greatdeals.com.sg/tag/store-openings/feed/ | 200 (lib 403) | 10 | 10 | 2026-10-02 | browser | KEPT as `greatdeals_storeopen` |
| greatdeals_eatdrink2 | rss | https://www.greatdeals.com.sg/category/eat-and-drink/feed/ | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |
| lbr_food | rss | https://littlebigreddot.com/category/food-drinks/feed/ | 200 (lib 403) | 10 | 8 | 2026-10-03 | browser | KEPT as `littlebigreddot_food` |
| lbr_newopen | rss | https://littlebigreddot.com/category/new-openings/feed/ | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |
| lbr_food2 | rss | https://littlebigreddot.com/category/food-and-drinks/feed/ | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |
| eatbook_deals | rss | https://eatbook.sg/category/deals/feed/ | 200 (lib 403) | 10 | 9 | 2026-10-01 | browser | KEPT as `eatbook_deals` |
| eatbook_foodnews | rss | https://eatbook.sg/category/food-news/feed | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |
| eatbook_foodnews2 | rss | https://eatbook.sg/category/food/food-news/feed/ | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |
| eatbook_tag_deals | rss | https://eatbook.sg/tag/deals/feed/ | 200 (lib 403) | 10 | 10 | 2026-10-01 | browser | alive, same content as Deals category; category kept instead |
| eatbook_tag_newopen | rss | https://eatbook.sg/tag/new-openings/feed/ | 200 (lib 403) | 10 | 10 | 2026-09-21 | browser | KEPT as `eatbook_newopen` |
| sethlui_food | rss | https://sethlui.com/category/food/feed/ | 200 (lib 403) | 10 | 7 | 2026-10-03 | browser | KEPT as `sethlui_food` |
| sethlui_foodnews | rss | https://sethlui.com/category/food-news/feed/ | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |
| sethlui_tag_new | rss | https://sethlui.com/tag/new-restaurants/feed/ | 200 (lib 403) | 3 | 2 | 2026-05-31 | browser | stale (2026-05-31) |
| sethlui_tag_open | rss | https://sethlui.com/tag/new-opening/feed/ | 200 (lib 403) | 10 | 8 | 2026-06-25 | browser | stale (2026-06-25) |
| honey_eatdrink | rss | https://thehoneycombers.com/singapore/category/eat-drink/feed/ | 200 (lib 403) | 0 | 0 | - | - | 200 but feed parsed as 0 items; not kept |
| honey_news | rss | https://thehoneycombers.com/singapore/category/news/feed/ | 200 (lib 403) | 0 | 0 | - | - | 200 but 0 items; not kept |
| tsl_sales | rss | https://thesmartlocal.com/read/category/sales-promotions/feed/ | 404 | 0 | 0 | - | - | DEAD 404 |
| tsl_tag_1for1 | rss | https://thesmartlocal.com/read/tag/1-for-1/feed/ | 404 | 0 | 0 | - | - | DEAD 404 |
| tsl_food | rss | https://thesmartlocal.com/read/category/food-lifestyle/feed/ | 404 | 0 | 0 | - | - | DEAD 404 |
| dfd_a | rss | https://danielfooddiary.com/feed | 403 (lib 500) | 0 | 0 | - | - | BLOCKED 403 |
| dfd_b | rss | https://www.danielfooddiary.com/feed/ | 403 (lib 500) | 0 | 0 | - | - | BLOCKED 403 |
| dfd_c | rss | https://danielfooddiary.com/category/news/feed/ | 403 (lib 500) | 0 | 0 | - | - | BLOCKED 403 |
| mtc_a | rss | https://misstamchiak.com/feed/ | 404 | 0 | 0 | - | - | DEAD 404 |
| mtc_b | rss | https://www.misstamchiak.com/feed | 404 | 0 | 0 | - | - | DEAD 404 |
| mtc_c | rss | https://misstamchiak.com/category/food-news/feed/ | 404 | 0 | 0 | - | - | DEAD 404 |
| timeout_a | rss | https://www.timeout.com/singapore/restaurants/rss | 404 | 0 | 0 | - | - | DEAD 404 |
| timeout_b | rss | https://www.timeout.com/singapore/news/feed | 404 | 0 | 0 | - | - | DEAD 404 |
| lifestyleasia_a | rss | https://www.lifestyleasia.com/sg/feed/ | 202 (lib 403) | 0 | 0 | - | - | BLOCKED 202 empty body |
| lifestyleasia_b | rss | https://www.lifestyleasia.com/sg/gear/feed | 202 (lib 403) | 0 | 0 | - | - | BLOCKED 202 empty body |
| soshiok | rss | https://www.soshiok.com/feed/ | 200 (lib 403) | 0 | 0 | - | - | alive but 0 items parsed (200, 29 KB, not a feed) |
| hgw | rss | https://www.hungrygowhere.com/rss/ | 500 | 0 | 0 | - | - | DEAD 500 |
| tsl_feed2 | rss | https://thesmartlocal.com/feed/?s=1-for-1 | 200 | 10 | 9 | 2026-07-31 | library | WordPress search feed ?s=1-for-1 answers but newest is 2026-07-31 (stale) |
| whatshappening | rss | https://www.thepatriots.asia/feed/ | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |
| sgfoodonfoot | rss | https://sgfoodonfoot.com/feed/ | 0 | 0 | 0 | - | - | DEAD connection error |
| sethlui_tag_promo2 | rss | https://sethlui.com/tag/deals/feed/ | 200 (lib 403) | 10 | 5 | 2026-05-28 | browser | stale (2026-05-28) |
| mothership_s | rss | https://mothership.sg/tag/food/feed/ | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |
| st_food | rss | https://www.straitstimes.com/news/life/food/rss.xml | 404 | 0 | 0 | - | - | DEAD 404 |
| st_foodrss2 | rss | https://www.straitstimes.com/news/life/rss.xml?x=1 | 200 | 39 | 8 | 2026-10-03 | library | alive, not kept |
| cna_sg2 | rss | https://www.channelnewsasia.com/rssfeeds/8395986 | 200 | 20 | 4 | 2026-10-03 | library | alive, general news; not kept |
| cna_life2 | rss | https://www.channelnewsasia.com/rssfeeds/8395884 | 200 | 20 | 2 | 2026-10-03 | library | alive 2/20 F&B (cna_lifestyle kept at 7/20) |
| goodyfeed_food | rss | https://goodyfeed.com/category/food/feed/ | 200 (lib 403) | 10 | 9 | 2026-07-10 | browser | alive but newest 2026-07-10 (stale) |
| goodyfeed_deals | rss | https://goodyfeed.com/category/deals/feed/ | 200 (lib 403) | 10 | 7 | 2024-10-05 | browser | stale (2024) |
| sg_ladyiron_food | rss | https://www.ladyironchef.com/category/restaurants/feed/ | 200 | 20 | 15 | 2026-09-29 | library | alive, not kept |
| tg_sgfoodpromo | telegram | https://t.me/s/sgfoodpromo | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgfoodcheap | telegram | https://t.me/s/sgfoodcheap | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgfoodnews | telegram | https://t.me/s/sgfoodnews | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgnewfoodopenings | telegram | https://t.me/s/sgnewfoodopenings | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgnewopenings | telegram | https://t.me/s/sgnewopenings | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgfoodsale | telegram | https://t.me/s/sgfoodsale | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgfoodpromos_official | telegram | https://t.me/s/sgfoodpromos_official | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_foodpromosg | telegram | https://t.me/s/foodpromosg | 200 | 8 | 7 | 2023-11-12 | library | alive but stale (newest 2023-11-12) |
| tg_singaporefoodpromo | telegram | https://t.me/s/singaporefoodpromo | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgcafehopping | telegram | https://t.me/s/sgcafehopping | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgdealsandpromos | telegram | https://t.me/s/sgdealsandpromos | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_lobangs | telegram | https://t.me/s/lobangs | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_mothership_food | telegram | https://t.me/s/mothership_food | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_danielfooddiary | telegram | https://t.me/s/danielfooddiary | 200 | 20 | 12 | 2026-10-01 | library | KEPT as `tg_danielfooddiary` |
| tg_sethluisg | telegram | https://t.me/s/sethluisg | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_thesmartlocalsg | telegram | https://t.me/s/thesmartlocalsg | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_hungrygowhere | telegram | https://t.me/s/hungrygowhere | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_kopitiamsg | telegram | https://t.me/s/kopitiamsg | 200 | 16 | 0 | 2026-05-31 | library | alive but stale and not F&B (0 F&B) |
| tg_sgkopitiam | telegram | https://t.me/s/sgkopitiam | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgfoodtrend | telegram | https://t.me/s/sgfoodtrend | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgbubbletea | telegram | https://t.me/s/sgbubbletea | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgdailydeals | telegram | https://t.me/s/sgdailydeals | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| tg_sgdealsfood | telegram | https://t.me/s/sgdealsfood | 200 | 0 | 0 | - | - | no such public channel (0 messages in t.me/s page) |
| misslobang | rss | https://misslobang.com/feed/ | 308 | 0 | 0 | - | - | NO FEED: 307 to www then 308 to /feed which is a Next.js 404 (also /rss.xml, /feed.xml) |
| misslobang_www | rss | https://www.misslobang.com/feed/ | 308 | 0 | 0 | - | - | NO FEED (see misslobang) |
| bykido | rss | https://bykido.com/feed/ | 404 | 0 | 0 | - | - | DEAD 404 |
| confirmgood | rss | https://confirmgood.com/feed/ | 200 | 10 | 5 | 2026-10-02 | library | KEPT as `confirmgood` |
| confirmgood_www | rss | https://www.confirmgood.com/feed/ | 0 | 0 | 0 | - | - | DEAD 0 |
| therantingpanda | rss | https://www.therantingpanda.com/feed/ | 200 | 15 | 13 | 2026-10-01 | library | KEPT as `therantingpanda` |
| citynomads | rss | https://citynomads.com/feed/ | 200 (lib 403) | 10 | 1 | 2026-10-01 | browser | alive, 1/10 F&B in feed; not kept |
| fzine | rss | https://fzine.com/feed/ | 200 (lib 403) | 10 | 3 | 2026-10-03 | browser | alive, 3/10; not kept |
| sassymama | rss | https://www.sassymamasg.com/feed/ | 200 (lib 403) | 100 | 7 | 2026-10-01 | browser | alive but 4.5 MB and 7/100 F&B; not kept |
| danamic | rss | https://danamic.sg/feed/ | 0 | 0 | 0 | - | - | DEAD connection error |
| littledayout | rss | https://www.littledayout.com/feed/ | 200 | 10 | 3 | 2026-10-02 | library | alive, family events, 3/10; not kept |
| harpersbazaar_sg | rss | https://www.harpersbazaar.com.sg/feed/ | 200 (lib 403) | 10 | 1 | 2026-10-02 | browser | alive, lifestyle, 1/10; not kept |
| misslobang_cat | rss | https://misslobang.com/category/food-deals/feed/ | 308 | 0 | 0 | - | - | NO FEED (see misslobang) |
| qsrmedia | rss | https://qsrmedia.asia/feed/ | 404 (lib 403) | 0 | 0 | - | - | DEAD 404 |

## Notes on the unusual ones

- **Telegram**: `t.me/s/<handle>` returns HTTP 200 with a ~9.6 KB shell page for handles that do not exist (0 messages), so only trust items > 0 and a fresh `<time datetime=`. Real, fresh F&B channels: `sgfooddeals`, `kiasufoodies`, `sgfoodies`, `danielfooddiary` (plus `eatbooksg`, a duplicate of the Eatbook feed). `sgkiasufoodies`/`SGKiasuFoodies` is a different, dead page.
- Telegram text is HTML-escaped (`&#036;` for `$`, `&amp;`, `&#39;`): unescape before classifying.
- **danielfooddiary.com/feed** is 403 from both UAs; its Telegram channel carries the same `[NEW] ...` opening posts and works.
- **misslobang.com** (a good aggregator seen in Google News) is a Next.js app with no RSS at all.
- **Google News** returns items from real SG F&B publishers (Eatbook, Great Deals, TheSmartLocal, misslobang, Confirm Good, Straits Times, CNA) so it is the only way to see misslobang/bykido/Time Out/Harper's roundups. Items are links to news.google.com redirects; titles end in ` - Publisher`.
- Fixtures trimmed: header + 5 items; `content:encoded` blocks removed from RSS fixtures to stay under 30 KB.

## Sample titles per kept source (verbatim, newest first)

### singpromos (rss, deals/promo)

- 4Fingers S’pore: 4pcs Wingettes & Drumettes for S$4 on 4 Oct 2026
- Springleaf Prata Place gives away 2 free plain prata on 6 Oct 2026
- Guzman y Gomez S’pore $3 Brekkie Burritos on 3 Oct 2026
- Burger King S’pore App Deals from S$1.50 Till 31 Dec 2026
- KFC S’pore Most Anticipated Chicken Tuesday Returns at $10.95 on Tuesdays till 10 Nov 2026
- LiHO TEA S’pore unveils Disney Princess Royal Tea Time drinks & collectibles
- (Updated 2 Oct 2026) Best Singapore Fixed Deposit Rates and Savings Accounts
- 108 Matcha Saro S’pore Selling Two Soft Serves for Just $6.99 (U.P. $10) until 7 Oct 2026

### tg_sgfooddeals (telegram, social/promo)

- 6 Food Events Happening This Oct 😋 🔹 Check out these night bazaars, food fairs & festivals happening around SG: 1️⃣ NAT Cultural & Food Festival (Till 4 Oct) 2️⃣ TLM Food Expo (Til ...
- TWOWORLDS: 1-for-1 Matcha Drinks 🍵 🔹 Enjoy 1-for-1 on TWOWORLDS’ new cold foam matcha drinks 🔹 Score an additional free banana pudding to elevate your matcha experience 📅 2 - 4 Oct ...
- Food Delivery Promo Codes (Oct 2026) 🛵 1️⃣ foodpanda: tco.sg/ahWN0BXhY 2️⃣ GrabFood: tco.sg/GKlKkU4IS @sgfooddeals #deals
- Free BreadTalk Hazel Cacao Bun with Nutella 🍞 🔹 Redeem a free BreadTalk Hazel Cacao Bun with Nutella when you spend $10 on Nutella spreads at major supermarkets 🔹 Enjoy BreadTalk’s ...
- Ongoing International Coffee Day Deals ☕️ 1️⃣ Borderless Coffee : Free Upsize (1 Oct) 2️⃣ Cedele : Free Coffee with purchase (1 Oct) 3️⃣ Gourmet Carousel : Free Coffee-based Drinks ...
- $2.99 coffee & sure-win game at Luckin Coffee's 100th store ☕ 🔹 Celebrate Luckin Coffee's 100th store opening with a $2.99 drink voucher at all outlets for members daily till 2 O
- D'Cuisine: $10 Lunch Buffet 🐠 🔹 Enjoy an Asian fusion lunch buffet with weekly rotating menu for just $10 🔹 Expect dishes like Salted Egg Prawns, Signature Curry Fish Head, Briyani ...
- Beard Papa's: 1-for-1 Opening Promo 🥐 🔹 Enjoy exciting 1-for-1 opening deals on Beard Papa's signature Custard Pie Cream Puff 📅 Now till 30 Sep 📍 Bugis Junction, B1-K05A Find out m ...

### tg_kiasufoodies (telegram, social/promo)

- 🥤 Beutea 🥤 ✅ 50% off all coffee series drinks ✅ Till 11 Oct ✅ Redeem via app 🔴 T&Cs apply, more info here @kiasufoodies
- 🧁 rrooll 🧁 ✅ $0.50 cinnamon roll ✅ 4 Oct, from 1pm 📍 All outlets 🔴 100 redemptions per outlet 🔴 T&Cs apply, more info here @kiasufoodies
- 🥞 Kremi 🥞 ✅ $1 for 2nd crepe ✅ 3-4 Oct 📍 *SCAPE 🔴 T&Cs apply, more info here @kiasufoodies
- 🍧 Soft Spot 🍧 ✅ 1-for-1 Turkish Dream ✅ 3 Oct 📍 Joo Chiat 🔴 T&Cs apply, more info here @kiasufoodies
- 🍕 Pizza Hut 🍕 ✅ 10.10 online exclusive deals ✅ 1-20 Oct ✅ Order via web or app 🔴 T&Cs apply, more info here @kiasufoodies
- SG Kiasu Foodies [Discounts/Promos] pinned a photo
- 💰 Promo Codes Oct 2026 💰 🐼 foodpanda: foodpanda.sg 🍀 GrabFood: grab.com/sg/food @kiasufoodies
- 🥤 TWOWORLDS 🥤 ✅ Buy 1 Matcha, get free Matcha + Banana Pudding ✅ 2-4 Oct, 12.30-5.30pm 📍 Jalan Pisang 🔴 T&Cs apply, more info here @kiasufoodies

### greatdeals_eatdrink (rss, deals/mixed)

- Hosen Singapore Is Giving Away FREE Supermarket Trolley Coin Keychains With $10 Spend This October
- Starbucks Singapore Debuts Protein Cold Foam For Coffee And Matcha Drinks
- CHAGEE Opens At Compass One And Sceneca Square With Tear & Win Prizes And 2 Large Milk Teas For $8.85
- KFC Chicken Tuesday Returns With 5pc Chicken for $10.95 Every Tuesday From October 6
- FairPrice’s Häagen-Dazs Weekly Offer Gives You 3 Pints for $25 Including Matcha, Pistachio & More
- PastaMania Singapore’s Children’s Day Deal Gives Kids a FREE Meal on October 2
- Shihlin Taiwan Street Food Reopens at The Seletar Mall With 1-FOR-1 Rice Bowls at $7.50
- Sushiro Opens at Hougang Mall on October 1 with 1-FOR-1 Sushi Deals and $1.50++ Free-Flow Drinks

### greatdeals_storeopen (rss, deals/opening)

- CHAGEE Opens At Compass One And Sceneca Square With Tear & Win Prizes And 2 Large Milk Teas For $8.85
- Shihlin Taiwan Street Food Reopens at The Seletar Mall With 1-FOR-1 Rice Bowls at $7.50
- Sushiro Opens at Hougang Mall on October 1 with 1-FOR-1 Sushi Deals and $1.50++ Free-Flow Drinks
- Beard Papa’s Bugis Junction Opens with 1-FOR-1 Custard Pie Cream Puffs for 3 Days
- PAWA Bakery Is Now Open At Jem With Buy 3 Get 1 FREE On All Bakes Till September 27
- PastaMania Opens At The Seletar Mall With FREE Pasta And Gelato Opening Deals
- More Yogurt Opens in AMK Hub with Buy 1 FREE 1 Yogurt Shakes on September 24 & 25
- Guzman y Gomez Northpoint City Reopens With S$5 Burritos & Bowls On September 24

### tg_sgfoodies (telegram, social/promo)

- 🍰 🎉 KIDS DINE FREE?! FAMILY MEAL PLANS JUST GOT SWEETER. 👧 🍽 💥 Here's the deal: 🆓 Kids dine FREE with every main course purchased 🍽 Enjoy a family meal without the extra little bil ...
- 🐟 🧦 FISH & CHIPS + $3 SOCKS?! THAT ESCALATED QUICKLY 👀 🔥 🍟 Dory Fish & Chips + canned drink for $15.90 🧦 Top up just $3 for a pair of NEW BFSF socks (U.P. $8.90) 🎨 Choo
- 🥐 🚨 BUY 1 FREE 1 CREAM PUFFS?! BUGIS, DON’T WALK 👀 🔥 🎉 Grand opening special at Bugis Junction 🥐 Buy 1 Free 1 Custard Pie Cream Puffs 👯 Perfect excuse to bring your cream puff budd ...
- 🍣 SUSHI PLANS? HOU GANG YOU! 🎉 Sushiro is opening at Hougang Mall with grand opening deals worth making a sushi run for! 👀 💥 What’s happening: 🍣 Selected sushi deals from $2.3++ 🐟 ...
- 🍮 💛 POMPOMPURIN MOONCAKES ARE BUY 1 FREE 1?! SANRIO FANS, RUN 👀 🥮 Get BUY 1 FREE 1 on the officially licensed Pompompurin Mooncake Gift Set 🍮 Includes Mao Shan Wang Mooncakes 🎁 Com ...
- 🍗 💸 PRE-PAYDAY BUT STILL CRAVING? $10 COMBOS TO THE RESCUE 👀 🔥 Good Deals 4 U is back with selected combos for just $10 each 💰 Perfect for the “saving money but still hungry” era 🍗 ...
- 🍰 💜 2 CHEESECAKE SLICES FOR $10?! SAY LESS 👀 🍰 Get 2 Chicago Cheesecake slices for just $10 ✨ Smooth, creamy & finished with that buttery biscuit base 👯 Share one with your bestie. ...
- 🍣 🚨 ALL SUSHI PLATES AT $1.50++?! THIS IS NOT A DRILL 👀 🍽 ALL qualifying plates at just $1.50++ 🤩 Choose from 80+ sushi varieties ⏰ Available from 3PM onwards ⏱️ Dining time limite ...

### eatbook_deals (rss, media/promo)

- KFC Has $25.95 One-Day Buffet At SCAPE: Unlimited Tenders, Bites And Sauces
- Get BreadTalk’s New Hazel Cacao Bun With Nutella For Free When You Buy $10 Worth Of Nutella
- There’s A New $29++ Peranakan High Tea In Joo Chiat With 14 Handmade Treats
- 10 Best Student Food Deals In Singapore 2026: $15.90++ K-BBQ, Free-Flow Drinks And More
- Get 50% Off This New Korean Buffet At Swissotel For A Limited Time
- Get $14.90++ Hotpot Sets At This 4.7-Star Restaurant In Holland Village
- Pizza Hut’s $19.95++ Dine-In Buffet Returns For A Limited Time
- HEYTEA ION Reopens With 1-For-1 Drinks For Three Days Only

### eatbook (rss, media/mixed)

- 28-Year-Old NUS Graduate Opens Hokkien Mee Stall In TPY: Here’s Our Honest Review
- First Look At Genki Sushi x Crayon Shinchan Collab: Limited-Time Menu And Merch
- We Tried 7-Eleven’s New Hot Food Bar, With DIY Bowls From $4.50
- 10 Best Food Deals In Oct 2026: 50% Off Korean Buffet, 1-For-1 Bubble Tea And More
- Japanese Hamburg Chain Opens First SG Outlet In CBD—Here’s Our Review
- KFC Has $25.95 One-Day Buffet At SCAPE: Unlimited Tenders, Bites And Sauces
- Um Yong Baek To Open At Suntec City With New Beef Bone Broth And More
- 10 New Restaurants And Cafes In Oct 2026: Viral Japanese Donuts, $28++ Pizza Buffet And More

### eatbook_newopen (rss, media/opening)

- New Chocolate Buffet At Pan Pacific Has Chocolate-Fed Wagyu, Chocolate Pasta And More
- Horizon Mall Opens In JB With 13 F&B Brands: HK Cha Chaan Teng, Nanyang Cafe And More
- 8 Eateries To Expect In 2025, Including The Long-Awaited Chick-fil-A
- Sakanoue Cafe Returns To SG With Famous Japanese Shaved Ice
- Beyond the Dough Review: Tokyo Neapolitan-Style Pizza By Japanese Chef Near Bugis MRT Station
- Popular Online Bakery Banele Opens Physical Store In Newton
- Jie Bakery Is Now Open In Farrer Park, Get Old-School Rainbow Bread Here
- Ralph’s Coffee Is Now Open In Orchard Road, The Second Ralph Lauren Cafe In SG

### littlebigreddot_food (rss, deals/mixed)

- TWG Tea opens 24-hour Tea Gallery with tea museum at Changi Airport T3
- WHUCHU Opens Beer Garden at UE Square With −86°C Frozen Beer
- Seoul tonkatsu and udon chain Ojeje opens first overseas outlet at Raffles City
- Millennium Hotels Launches ‘Moments That Matter’ for Breast Cancer Awareness Month
- The CHOYA Ginza BAR Opens in Singapore at Millenia Walk
- Starbucks Singapore Launches Protein Cold Foam From 7 October
- Fieldnotes opens dine-in café at Takashimaya with all-day brunch from S$18
- Void Deck Jam Vol. 2 at Design Orchard steps on Sunday 4 October from 3pm

### sethlui_food (rss, media/mixed)

- Tracy’s Sarawak Kitchen: Unique Eastern Malaysian dishes like money cai mee sua & tomato kway teow
- 6 new openings at The Exchange TRX to check out before 2026 ends
- Seoul’s famous tonkatsu spot OJEJE lands in Singapore
- The Neighbourwok Hokkien mee opens Serangoon eatery with kaya toast, laksa & dry ban mian
- 24 best buffets in Singapore: Ultimate all-you-can-eat guide for all occasions [Oct 2026]
- Matcha & Girls brings fashion, beauty, fitness & plenty of matcha to Toppen JB this weekend
- Ducoo: New hawker gourmet pasta from S$6 in Lavender
- 31-day Punggol Pasar Malam with squishy store, ayam gepuk, XXL mochi balls & more

### ladyironchef (rss, media/opening)

- I’m donut? Singapore – Popular Japanese Donut Brand Is Opening In Singapore
- Fika Swedish Cafe At Arab Street Is Closing After 17 Years
- Best Peking Duck In Singapore – 7 Restaurants You Need To Try
- Orh Gao Taproom & Peh Gao Coffeeshop – A Day-to-Night Dining Concept Worth Travelling To
- Marymount Bakehouse Review: Singapore’s Best Sourdough Café at Farrer Park
- Hajime Tonkatsu & Ramen Has Opened A Third Outlet At Dunearn Village
- Torikizoku – Japan’s Famous Yakitori Chain Is Opening In Singapore
- Relish at Cluny Court Is Closing on 29 March After 19 Years

### tg_danielfooddiary (telegram, social/opening)

- 20 NEW Cafes In Singapore October 2026 – Trendy Coffee Shops, Bakeries And Brunch Spots To Visit https://danielfooddiary.com/2026/10/01/cafesoct2026/ ☕ Other NEW Cafes In Singapore ...
- 🧽 October hawker centre closures to take note of. Some centres are closed for cleaning, while Kim Keat Palm Food Centre, West Coast Market Square and Changi Village Blk 2 and 3 hav ...
- I’m donut? Singapore – Viral Japanese Nama Donut Brand Reportedly Coming To SG. Plus 11 Other Donut Shops To Try In Singapore https://danielfooddiary.com/2026/09/29/donuts/ @Daniel ...
- Fuji Prawn Noodles 弗記傳承肉骨蝦麵 – Under-The-Radar Toa Payoh Prawn Mee For Supper With Big Prawns And Pork Ribs From $6.50 https://danielfooddiary.com/2026/09/25/fujiprawnnoodles/ #DFDT ...
- Soup Curry by Ki-setsu – NEW Hokkaido-Style Soup Curry Eatery At Fortune Centre With Chicken, Vegetables And Customisable Spice https://danielfooddiary.com/2026/09/26/soupcurrybyki ...
- Dolpan Hwajoo – Busan-Born Korean Restaurant Opens At Tanjong Pagar With Hot-Stone Sharing Dishes And Ube Makgeolli https://danielfooddiary.com/2026/09/24/dolpanhwajoo/ #DFDKorean ...
- Onggii – Korean Gomtang Specialist Opens NEW Square 2 Outlet With Samgyetang And Hanok-Inspired Interiors https://danielfooddiary.com/2026/09/24/ongginovena/ #DFDKorean 🐔 Other Sam ...
- Noci Bakehouse – NEW Orchard Gateway Outlet With Exclusive Panuozzo, Korean-Style Bagels And Cream Coffee https://danielfooddiary.com/2026/09/23/nociorchard/ ☕ Other NEW Cafes in S ...

### therantingpanda (rss, media/mixed)

- Food Review: OJEJE At Raffles City | Seoul’s Tonkatsu & Udon Restaurant First International Foray In Singapore
- Food Scoops: New and Buzzing Singapore Restaurants In October 2026
- Hotel Review: The St. Regis Shanghai Jingan | Excellent Location & City View, Dated Facilities
- Food Review: AO Restaurant At Claymore Drive | Casual Japanese-Led Concept By Ex-Esora Chef
- Food Scoops: Best Cafés To Check Out In Joo Chiat And Katong | Guide To Your Coffee And Brunch Fix In East Coast
- Food Review: Po Restaurant At The Warehouse Hotel | Modern Peranakan Cuisine In Robertson Quay
- Food Review: Osteria Mozza Singapore At ION Orchard | Chef Nancy Silverton’s Only Asian Outpost
- Snippets: The Complete Guide To Michelin Key Hotels Singapore 2026

### confirmgood (rss, deals/promo)

- KFC’s Chicken Tuesday Returns at S$10.95 & Chicken Buffet at S$25.95
- Singapore’s Best Halloween Spots to Check Out
- Everything CHOYA – Singapore’s first dedicated CHOYA Ginza Bar
- Skechers now has a pickleball collection, including paddles
- Visit PLQ now till 1 November for vouchers, Lendlease Plus points & F&B deals
- We enjoyed nasi lemak & laksa with a waterfall view at Wild Coco at Jewel
- Singapore Dog Festival Returns with Tail-Wagging Fun
- Ushio Sumiyaki & Sake Bar: An Izakaya Escape at OUE Tower

### thesmartlocal (rss, media/promo)

- LEGO F1 Experience The Thrill At Suntec City: Life-Sized LEGO F1 Car & Game Booths With Freebies
- 12 Singapore IC & Passport Facts You Probably Didn’t Know, Like What The S & T On Your IC Mean
- Get Up To $35 Off Food & Shopping With DBS/POSB Card Deals For The Best F1 Weekend At Home
- You Can See Saturn & “Shooting Stars” In SG This October – Here’s When & Where To Catch Them
- Singapore Writers Festival 2026 Returns This November With Jemimah Wei, Amitav Ghosh & A Crime Fiction Track
- All You Need To Know About The Revised Medical Classification System Replacing PES Status For NS Enlistees
- Guide To The SG Culture Pass: What Is It & What Can The $100 Credits Be Used For?
- 14 Best Things To Do This Weekend In Singapore – 2nd-4th October 2026

### honeycombers (rss, media/mixed)

- This By Invite Only x Polly Pocket collection in Singapore is made for Y2K nostalgics
- Where to find delectable Deepavali snacks in Singapore
- What’s happening in Singapore: Your lowdown on the trending news this week
- 15 best brunch spots in Singapore for all-day breakfast and weekend indulgence
- Set lunch in Singapore: 14 restaurants serving value executive meals
- F1 drivers in Singapore: How (and where) you might spot them
- 35 best cafes in Singapore for coffee, brunch and cafe hopping
- 27 best wedding venues in Singapore to tie the knot: From affordable garden settings to grand hotel ballrooms

### straitstimes_life (rss, news/mixed)

- Stray Kids join BTS in skipping Grammy submissions
- Giant robot, masks, flames: The Weeknd returns to S’pore with a bigger, grander show
- The Straits Times Weekly Bestsellers Oct 3
- Four bars that embrace art, history and travel
- The Lunch Break Investor author Thomas Chua seeks out books that disagree with him
- Try Caribbean food for a limited time at Ricardo’s Chop and Jerk
- Hadramawt Kitchen reopens at Hotel Boss with new Yemeni dishes
- Kasan Goh casts off literary inheritance of dad Goh Poh Seng in debut novel on squatting in London

### cna_lifestyle (rss, news/mixed)

- Philippines voices concern over Myanmar airstrike deaths, injuries
- Fast cars, slow queues: Malaysia hosts F1 race after 9 years, but some fans fume
- Between 'frustration' and 'good news', RTS Link delay triggers contrasting reactions across Causeway
- Spotting pygmy elephants, eating UFO tarts: Why Sandakan should be on your Sabah travel list
- US arrests man over alleged smuggling of US$300 million worth of computer servers to China
- Thai Airways chief says he was fired by board after Bangkok flood chaos
- 'I could not let all those people die': Wounded flydubai pilot describes moment he realised plane was going down
- Can AI help Hong Kong’s struggling comic book industry turn the page?

### gnews_promo_fnb (gnews, news/promo)

- 19 Best Deals In Singapore This Week – 28th September-4th October 2026 - TheSmartLocal
- 20 Restaurant Promotions and Dining Deals in Singapore This October 2026 - bykido.com
- 10 Best Food Deals In Oct 2026: 50% Off Korean Buffet, 1-For-1 Bubble Tea And More - Eatbook.sg
- Coffee Day deals: a free cup, Luckin coupons and S$1,000 beans - DANAMIC
- Shoppers can get cheaper chicken and eggs at FairPrice supermarkets until Dec 31 - The Straits Times
- Best Children’s Day 2026 Deals to Check Out - Confirm Good
- Foodpanda Offers S$6 Off Food Delivery Ahead of Singapore Grand Prix - Alvinology
- Set lunch in Singapore: 14 restaurants serving value executive meals - Honeycombers

### gnews_1for1 (gnews, news/promo)

- 10 Best Food Deals In Oct 2026: 50% Off Korean Buffet, 1-For-1 Bubble Tea And More - Eatbook.sg
- 19 Best Deals In Singapore This Week – 28th September-4th October 2026 - TheSmartLocal
- Sushiro Opens at Hougang Mall on October 1 with 1-FOR-1 Sushi Deals and $1.50++ Free-Flow Drinks - Great Deals Singapore
- 1-for-1 mattress deals & up to 80% off at Four Star's Clearance Roadshow Fair in Bugis from Sep. 30 to Oct. 4 - Mothership
- 20 Restaurant Promotions and Dining Deals in Singapore This October 2026 - bykido.com
- Coffee Day deals: a free cup, Luckin coupons and S$1,000 beans - DANAMIC
- Sushiro Hougang Mall Opens With Rotating 1-for-1 Sushi and $1.50++ Free-Flow Drinks (1-14 Oct 2026) - misslobang.com
- Singapore inks carbon trading pact with Peru - Singapore Economic Development Board (EDB)

### gnews_chain_promo (gnews, news/promo)

- Starbucks Unveils Meowchestra Halloween Collection With Cat-Themed Tumblers and Plushies - Great Deals Singapore
- 20 Restaurant Promotions and Dining Deals in Singapore This October 2026 - bykido.com
- Would You Work at Starbucks for Free? - Psychology Today
- McDonald’s Singapore brings G-DRAGON to its latest K-campaign - QSR Media Asia
- 19 Best Deals In Singapore This Week – 28th September-4th October 2026 - TheSmartLocal
- 10 Best Food Deals In Oct 2026: 50% Off Korean Buffet, 1-For-1 Bubble Tea And More - Eatbook.sg
- KFC’s Chicken Tuesday Returns at S$10.95 & Chicken Buffet at S$25.95 - Confirm Good
- KFC Gen B Buffet: Unlimited O.R. Tenders and Chicken Bites for $25.95 at KFC *SCAPE, Fri 16 Oct 2026 - misslobang.com

### gnews_buy1get1 (gnews, news/promo)

- 19 Best Deals In Singapore This Week – 28th September-4th October 2026 - TheSmartLocal
- 10 Best Food Deals In Oct 2026: 50% Off Korean Buffet, 1-For-1 Bubble Tea And More - Eatbook.sg
- Users report smooth recycling process as beverage container return scheme fully kicks in on Oct 1 - The Straits Times
- Retailers race to label or remove unmarked stock as beverage container return scheme’s transition period ends - CNA
- 20 Restaurant Promotions and Dining Deals in Singapore This October 2026 - bykido.com
- Coffee Day deals: a free cup, Luckin coupons and S$1,000 beans - DANAMIC
- PastaMania Singapore’s Children’s Day Deal Gives Kids a FREE Meal on October 2 - Great Deals Singapore
- Best Children’s Day 2026 Deals to Check Out - Confirm Good

### gnews_free_food (gnews, news/promo)

- 19 Best Deals In Singapore This Week – 28th September-4th October 2026 - TheSmartLocal
- 10 Best Food Deals In Oct 2026: 50% Off Korean Buffet, 1-For-1 Bubble Tea And More - Eatbook.sg
- Coffee Day deals: a free cup, Luckin coupons and S$1,000 beans - DANAMIC
- Woman wins S$1,600 McDonald's voucher, goes all over HK treating strangers to free meals - Mothership
- An overview: Best credit card promotions in Singapore (October 2026) - MoneySmart
- 29 New Family-Friendly Things To Do In October 2026 With Kids In Singapore - Little Day Out
- IKEA Singapore Is Giving Kids FREE Oat Vanilla Ice Cream On October 2 This Children’s Day - Great Deals Singapore
- Dunkin', L.L. Bean launch merch collab with free coffee giveaway - Yahoo News Singapore

### gnews_first_outlet (gnews, news/opening)

- Viral Japanese bakery I’m Donut? to open outlet in Singapore - Yahoo News Singapore
- I'm Donut to open first Singapore bakery in 2026 - UA.NEWS
- 5 Best New Restaurants In Singapore: October 2026 - Sassy Mama Singapore
- Trump's Second Term Is Creating A New Family Separation Crisis: Atlantic - Yahoo News Singapore
- Celebrities pay tribute to Tun Dr Siti Hasmah Mohamad Ali - Yahoo Lifestyle Singapore

### gnews_flagship (gnews, news/opening)

- I'm Donut, the viral Japanese bakery chain, opening first Singapore outlet - CNA Lifestyle
- Viral Japanese bakery I’m Donut? to open outlet in Singapore - The Straits Times

### gnews_overseas_brand (gnews, news/opening)

- China’s Luckin Coffee marks 100th store, 1.9m app members in Singapore - The Straits Times
- 10 New Restaurants And Cafes In Oct 2026: Viral Japanese Donuts, $28++ Pizza Buffet And More - Eatbook.sg
- 5 Best New Restaurants In Singapore: October 2026 - Sassy Mama Singapore
- Luckin Coffee has 100 outlets in Southeast Asia's smallest country - VnExpress International

### gnews_new_opening (gnews, news/opening)

- Just Opened August 2026: New Restaurants, Cafes and Bars in Singapore - City Nomads
- 5 New Restaurants In Singapore To Check Out This October 2026 - Time Out Worldwide
- 19 Best Deals In Singapore This Week – 28th September-4th October 2026 - TheSmartLocal
- New Restaurants, Cafes And Bars In Singapore: October 2026 - Harper's Bazaar Singapore
- Food Scoops: New and Buzzing Singapore Restaurants In October 2026 - The Ranting Panda
- The Singapore Edition replaces Fysh with Asian-inspired Tanica - The Business Times
- Tanjong Pagar Food Guide: 20 Places For Michelin-Approved Pizza, Korean Knife-Cut Noodles And More - Eatbook.sg
- 10 Best New Cafes & Restaurants In Singapore In October 2026 - FZINE Singapore

### gnews_bubbletea (gnews, news/mixed)

- Chagee opening more heartland stores in S’pore following customer demand - Mothership
- Viral Molly Tea To Open At Hillion Mall On 9 Oct: 1-For-1 Drinks, Free Tumblers And More - Eatbook.sg
- $209k just to open: Tea shop founder breaks down cost of opening a store in Singapore, Lifestyle News - asiaone.com
- PlayMade 1-for-1 Reopening Special at Westgate & Waterway Point: 5 Drinks From $2.10 a Cup, 2 & 3 October Only - misslobang.com
- 5 Best New Restaurants In Singapore: October 2026 - Sassy Mama Singapore
- Things To Do In Singapore This Weekend: 2 To 4 October - Harper's Bazaar Singapore
- Ging Sun Ho launches Singapore-exclusive menu with $9.90 combo - Confirm Good
- 19 Best Deals In Singapore This Week – 28th September-4th October 2026 - TheSmartLocal


## Scraper / API probe (2026-10-03, residential SG IP, Chrome UA, urllib)

Items for kept sources = dry-run counts. robots verdict = `urllib.robotparser` on the fetched robots.txt for the path used.

| candidate | url | status | robots | items | verdict |
|---|---|---|---|---|---|
| misslobang food | https://www.misslobang.com/category/food | 200, 1.7 MB | Allow: / | 200 cards in HTML, 74 after 60-day filter | KEPT `misslobang_food`. Server-rendered Next.js cards (h3, standfirst, deal badge); date on some cards only |
| misslobang deals | https://www.misslobang.com/category/deals | 200, 4.2 MB | Allow: / | 463 cards, 80 taken, ~21 F&B | KEPT `misslobang_deals`. Not newest-first; mixes retail/travel |
| DBS/POSB dining | https://www.dbs.com.sg/personal/promotion/cards-wonderful-dining | 200, 229 KB | allowed | 46 cards, 39 unique | KEPT `dbs_dining`. Cards sit in a `<noscript>` block; standing offers, no dates |
| HungryGoWhere home | https://www.hungrygowhere.com/ | 200, 98 KB | only `*/page/*` disallowed | 8 cards, dated, several "New Openings" | KEPT `hungrygowhere`. Its /feed/ and /food-news/ answer 500 |
| DBS card-promotions hub | https://www.dbs.com.sg/personal/cards/card-promotions | 200, 393 KB | allowed | n/a | superseded by the dining page (hub is generic, all categories) |
| OCBC card promotions | https://www.ocbc.com/personal-banking/cards/card-promotions?main=foodandgroceries | 200, 139 KB | allowed | 0 | REJECTED: merchant list loaded by JS ("promotions found"), no JSON URL in page or page-script.js; also `?main=` variants identical |
| UOB cards deals | https://www.uob.com.sg/personal/promotions/cards/deals/index.page | 200, 463 KB | not checked | ~60 modals | REJECTED: hotel/travel/ticket-heavy standing offers in modals, little F&B deal text; dining paths (`/dining.page`, `/dining-privileges.page`) 404 |
| HSBC / Citi / AMEX SG | hsbc.com.sg/credit-cards/, citibank.com.sg/, americanexpress.com/sg/ | 200 | not checked | 0 dining deals | REJECTED: marketing homepages only; guessed dining paths 404 |
| Chope deals | https://www.chope.co/singapore-restaurants | 200, 249 KB | `/passport`, `/user` only | page says "Our Deals have Moved" | REJECTED: deals moved to Grab Dine Out |
| Grab Dine Out | https://www.grab.com/sg/restaurant-deals/ | 200, 164 KB | not checked | 0 | REJECTED: marketing page, deals are in the app |
| Eatigo | https://eatigo.com/sg/singapore/en (+ /sg, www) | 308 / 404 / 525 | allowed | 0 | REJECTED: redirect loop / origin error, Nuxt app |
| Burpple | https://www.burpple.com/ | 200 but Cloudflare challenge marker | Crawl-delay 10, AI bots disallowed | 0 | REJECTED: bot wall |
| foodpanda SG | https://www.foodpanda.sg/ | 200, 870 KB | not checked | 0 deals text | REJECTED: app shell, no promo list in HTML |
| Deliveroo SG offers | https://www.deliveroo.com.sg/offers | 200, 190 KB | not checked | 0 | REJECTED: Next shell, offers need location + JS |
| Domino's SG promotions | https://www.dominos.com.sg/promotions | 200, 184 KB | not checked | ~6 | REJECTED: hand-edited CMS tiles with no per-item URL, 6 standing offers |
| Subway SG | https://www.subway.com/en-sg/promotions | 200, 251 KB | not checked | 0 | REJECTED: no deal text in HTML |
| KFC SG | https://www.kfc.com.sg/promotions | 200, 34 KB | not checked | 0 | REJECTED: JS app shell |
| Starbucks / BK / Pizza Hut / Jollibee / McDonald's SG | various | 200/404 | not checked | 0 | REJECTED: no deal list in server HTML (McDonald's deals URLs 404, Jollibee only a "Special Deals" banner) |
| LiHO, Mixue, KOI, Chagee SG | various | 0/404 | - | 0 | REJECTED: unreachable or 404 |
| Mall pages (CapitaStar, Jewel, Frasers, Mapletree, VivoCity, ION, Suntec) | various | 200/403/0 | not checked | 0 | REJECTED: shells without dining-promo lists in HTML; ION 403; Suntec domain unreachable; Jewel promotions path 404 |
| QSR Media Asia RSS | https://qsrmedia.asia/rss.xml | 200, 21 KB | `/rss.xml` allowed | ~20 | REJECTED: titles are standfirsts ("The company withdrew from the market in 2019."), real headline only in the URL slug; Asia-wide, would need a Singapore filter |
| MoneySmart dining promos | https://www.moneysmart.sg/dining-promotions | 403 | - | 0 | REJECTED: bot wall |
| Time Out SG new restaurants | https://www.timeout.com/singapore/restaurants/new-restaurants-in-singapore | 404 (binary body) | - | 0 | REJECTED |

### Free-key APIs (not signed up, no key held)
- GNews.io: 100 requests/day, 10 articles/request, 12-hour delay, non-commercial only (checked on its pricing page 2026-10-03). Env var would be `GNEWS_API_KEY`. Adds little: it indexes the same outlets as the 12 Google News queries, and the 12 h delay hurts a freshness tool. Not recommended.
- NewsData.io: free tier exists (`NEWSDATA_API_KEY`), limits not verifiable from its pricing page when fetched. Same overlap argument. Not recommended.
