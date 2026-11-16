# BiOLoVE Variant Wiki

提供公開 ClinVar 快照、各位點的中文解讀，以及實驗室自己的判讀歷程。企業識別使用提供的 BiOLoVE 圖檔。

## 閱讀首頁

雙擊 `index.html` 即可離線閱讀；也可上傳到 GitHub Pages。以基因、HGVS 或 VCV 搜尋，點選位點後可查看中文說明、可能影響、來源、ClinVar 版本歷程及實驗室判讀。教學模擬已移除。

中文解讀是有來源與查核日期的編輯摘要，並非另一個 ClinVar 分類；疾病的一般表現與變異相關證據會分別說明。本站分類為最近一次收錄版本，不保證即時更新。

## 直接輸入並儲存實驗室判讀

在本專案資料夾執行（只需 Python 3，不需額外套件）：

```sh
python3 scripts/serve.py
```

然後開啟 http://127.0.0.1:8765 。也可雙擊 `開啟判讀編輯器.command`，再依終端機顯示的網址開啟。若連接埠已被使用，可加上 `--port 8766`。按 Ctrl+C 停止。

1. 在右側表單選取或輸入基因及位點，或展開位點後按「＋ 新增判讀」。
2. 填實際判讀日期、分類、適用疾病／範圍及判讀原因。依據可包含證據代碼、文獻或與前次不同之處。只填可公開的變異層級內容，不含個案識別資訊。
3. 確認頁面顯示「本機編輯模式」，按「儲存並重建首頁」。紀錄會直接追加到 `data/lab.json`，保留歷史，並重建 `index.html`。同一筆重送不重複新增；日期不得早於既有紀錄。同日可保存多筆不同判讀。
4. 重開首頁仍能看到正式紀錄。更新 GitHub Pages 時，重新上傳重建後的首頁、資料及 assets。

編輯器僅綁定本機 127.0.0.1，不是公開網站的共享後端。公開靜態網站的訪客不能直接修改專案資料。

## 離線／GitHub Pages 表單模式

雙擊檔案或在 GitHub Pages 填表時，「儲存本機草稿」只保存於該瀏覽器 localStorage，會在位點歷程標為「本機草稿・尚未寫入專案」。不會自動寫回硬碟或公開網站，清除瀏覽器資料也會移除草稿。若瀏覽器不支援保存，頁面會回報失敗。

- 按「匯出完整 lab.json」下載包含既有正式紀錄及本機草稿的 JSON；由維護者核對後放入 `data/lab.json`，執行 `python3 scripts/build.py`。多人各自匯出的檔案須先合併並核對，不直接覆蓋他人新增紀錄。
- 同一瀏覽器、同一本機編輯器網址有草稿時，按「將本機草稿寫入專案」可逐筆正式保存；成功的草稿才會移除。不同來源（file、GitHub Pages、localhost）的 localStorage 各自獨立，不會自動轉移。
- 匯出本身不會移除草稿。重新開啟已包含相同 record_id 的正式首頁時，不再顯示該筆為待存檔草稿。

## 資料與版型

- `data/variants.json`：ClinVar 位點與追加式 history，以及 explanation（summary、impact、context、checked_on、sources）。來源分類及版本不得因中文說明而改寫。
- `data/lab.json`：實驗室判讀，依 accession 對應同一 ClinVar 位點；儲存獨立 history，每筆含 revision、date、classification、scope、note 及表單產生的 record_id。revision 是實驗室紀錄序號，非 VCV 版本。
- `template.html`：版面與插入點；`assets/style.css`、`assets/app.js`：樣式與互動。
- `assets/biolove-*.png`：使用者提供的企業識別圖檔；未引用外部字型或分析服務，離線可閱讀。
- `scripts/build.py`：驗證來源並產生首頁。
- `scripts/serve.py`：提供本機寫入 API 與首頁；不對外開放，也不提供任意路徑寫入。

```sh
python3 scripts/build.py
python3 -m unittest discover -s tests
```

## 新增位點或更新 ClinVar

依 `AGENTS.md` 核對 NCBI ClinVar 原始 VCV 紀錄。首次建立基準快照；既有位點僅追加新版、保留舊版及原日期；同版本不重複加入。無法核實則暫緩納入。完成後重建首頁，回報更新位點、分類差異及修改檔案。

## GitHub Pages

將 `index.html`、`assets/`、`data/`、`template.html`、`scripts/`、`AGENTS.md`、`README.md` 上傳到 repository 根目錄。不要上傳 `work/` 暫存及測試資料。在 Settings → Pages 選 Deploy from a branch，設定 main 與 / (root)。GitHub Pages 提供閱讀與瀏覽器草稿功能，不會執行 Python 寫入 API。

首次輸入的實驗室位點依基因、轉錄本、HGVS 建立 LAB: 識別碼並加入索引。判讀結果可自行輸入。首頁統計索引中的不同基因及位點，正式判讀筆數只計已存檔紀錄。
