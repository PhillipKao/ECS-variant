# Variant Wiki 專案規則

## 目的與交付
讓讀者查到「本站最近一次收錄時，ClinVar 如何分類這個位點」，並保留後續版本的差異。同一位點呈現中文解讀、可能影響、ClinVar 快照及實驗室判讀歷程。沿用相同資料結構與版型。介面與摘要用繁體中文，HGVS、ClinVar 分類及 review status 保留原文。移除教學模擬，不新增虛構判讀。

## 目錄與責任
- data/variants.json 是 ClinVar 真實資料及中文解讀的唯一編輯入口。每個 VCV 對應一個位點物件。
- data/lab.json 獨立保存實驗室判讀資料，以 accession 或實驗室位點識別碼對應索引；在首頁合併呈現，但來源及歷程不得混淆或彼此覆寫。
- template.html 控制版型與表單，保留 RECORDS 及 STATE 插入點。assets/style.css、assets/app.js 控制樣式與互動。企業識別使用使用者提供的 BiOLoVE 圖檔。
- scripts/build.py 驗證資料並產出 index.html。改版型、樣式、互動或資料後一律重建首頁。
- scripts/serve.py 提供僅限本機的判讀寫入服務，寫入資料後立即重建首頁；保持離線及 GitHub Pages 的靜態閱讀能力。
- README.md 記錄閱讀、編輯、草稿、匯出與發布流程，操作流程變更時同步更新。

## 新增或追蹤一個 ClinVar 位點
1. 開啟 NCBI ClinVar 的 VCV 頁面，核對基因、含版本的轉錄本、c.HGVS、蛋白標記及完整 VCV.version。網頁不可讀時可核對 NCBI 官方 E-utilities VCV XML。無蛋白標記時填空字串。來源無法核實時列出待補資料，暫緩納入。
2. 以不含版本號的 accession 搜尋既有物件。新位點從空的 history 開始。已存在者只在 history 尾端追加新版快照，保留舊版本及原日期。
3. date 為實際收錄日（YYYY-MM-DD），version 為 VCV 版本整數。classification 與 review 抄錄 Germline 彙整欄，scope 標示適用範圍，note 用一句中文記錄可核對的重點。保留 Conflicting 原文，避免以多數決取代彙整分類。
4. 同版本重查時不重複新增。版本前進而分類未變也可收錄，寫明實際觀察到的差別。若無法確認改版原因，記為「版本更新，原因未核實」。不得補造未曾核對的歷史或推估改判日期。
5. RCV 的疾病別判讀與 SCV 的個別提交不可取代 VCV 彙整結果。專家小組判讀指定疾病時，把病名寫進 scope。只收錄公開資料，勿加入個案識別資料。
6. 首次收錄只顯示基準點。更新時比較相鄰快照，顯示分類差異，歷程由新到舊排列。

## 中文解讀與可能影響
- 每個位點的 explanation 保存 summary（變異說明）、impact（可能影響）、context（遺傳及解讀限制）、checked_on（實際查核日期）、sources（title、url）。
- 使用 NCBI ClinVar、ClinGen、GeneReviews 或原始研究核對並提供來源連結；區分位點特異證據與疾病一般特徵。不得把基因的一般功能直接當作特定位點致病證據。
- 解讀需交代相關遺傳模式與基因型脈絡；不得將 Pathogenic 等同每位帶因者必然發病，也不得推估個人症狀。分類衝突如實說明，不以多數決改寫。
- 中文說明的查核日期獨立於 ClinVar history，不因此改寫已收錄分類或追加未核實版本。

## 實驗室判讀（公開）
- 表單分別輸入或選取基因、位點與判讀結果，填實際判讀日期、classification、scope 及 note（判讀依據，可含證據代碼與文獻）。缺資料時詢問，不得捏造。只收錄可公開的變異層級資訊，不含個案識別資料。
- 每個物件保存與 variants.json 一致的 gene、transcript、hgvs、protein、accession，以及獨立 history。每筆含 revision（從 1 遞增的實驗室序號，非 VCV 版本）、date、classification、scope、note，表單另產生 record_id 防止重送。
- 依實際判讀日期由舊到新追加、保留原紀錄及原日期；同一筆重送不重複新增，同日可追加不同紀錄，分類未變也可追加。
- 本機編輯器儲存後直接寫入 data/lab.json 並重建首頁。靜態／離線表單只存瀏覽器草稿，須明確標示未正式存檔；匯出資料不代表已更新專案或公開網站。
- 實驗室歷程與 ClinVar 歷程在同一位點內分欄或分區顯示，保留各自日期、分類、理由及來源。不得用實驗室結論覆寫 ClinVar。

## 完成條件
執行 python3 scripts/build.py。依基因、HGVS 或 VCV 測試搜尋及無結果情境；展開位點核對日期、版本、分類、來源、中文說明及實驗室歷程。新增判讀需驗證理由、追加、同筆不重複、重開後仍存在、失敗不回報成功。確認離線／靜態草稿提示及匯出。本機伺服器僅綁定 127.0.0.1，保持離線雙擊與 GitHub Pages 的閱讀能力。回報更新位點、分類變化與修改檔案。

首次輸入的實驗室位點依基因、轉錄本、HGVS 建立 LAB: 識別碼並加入索引。判讀結果可自行輸入。首頁統計索引中的不同基因及位點，正式判讀筆數只計已存檔紀錄。
