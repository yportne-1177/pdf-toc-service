



---



##### **## 0) Design snapshot**



\- \*\*Mode\*\*: Single bundle (exactly one of \*\*Tables\*\* or \*\*Figures\*\*).

\- \*\*Files\*\*: PDFs live in \*\*SharePoint\*\* and the \*\*desktop has the library synced\*\* via OneDrive. PAD runs your Python locally and writes to the synced folder. Sync propagates to SharePoint automatically.

\- \*\*Return\*\*: Cloud flow creates a \*\*sharing link\*\* and returns `{ status, outputPath, shareLink, error }` to Power Apps.



---



##### **## 1) Prereqs (one‑time on the desktop)**



1\) \*\*Install Python 3.x\*\* and put it on PATH.  

2\) Install libraries your script needs:

&nbsp;  ```bash

&nbsp;  pip install pypdf fpdf

&nbsp;  ```

3\) Place your script at (example):

&nbsp;  ```

&nbsp;  C:\\apps\\pdfbundle\\merge\_pdfs.py

&nbsp;  ```

4\) Verify script prints a line per output in the form:

&nbsp;  ```

&nbsp;  Created: C:\\...\\\_merged\_tables.pdf

&nbsp;  ```

&nbsp;  (Your doc shows the script already prints this. We’ll parse it in PAD.)



---



##### **## 2) OneDrive/SharePoint sync (one‑time)**



> Goal: identify the \*\*local sync root\*\* for your team library so PAD can translate site‑relative paths like `/Documents/pdf\_study/src` to a \*\*local\*\* path.



\*\*Steps:\*\*

1\) In \*\*SharePoint → Document Library\*\*, click \*\*Sync\*\* (top toolbar). Complete OneDrive sign-in if prompted.

2\) After sync starts, open \*\*File Explorer\*\* and locate the library. Typical patterns:

&nbsp;  - `C:\\Users\\<you>\\Contoso\\Shared Documents\\` (tenant/library root)

&nbsp;  - Inside there: `...\\Shared Documents\\pdf\_study\\src`

3\) Right‑click that \*\*root folder\*\*, choose \*\*Properties\*\*, copy the full path.  

&nbsp;  Example we’ll refer to as:

&nbsp;  ```

&nbsp;  localSyncRoot = C:\\Users\\<you>\\Contoso\\Shared Documents

&nbsp;  ```

> Keep this exact path—it’s used in the PAD flow to construct `localSrc` and `localOut`.



---



##### **## 3) Power Apps (Canvas) – final wiring**



\*\*Inputs (Modern controls)\*\*  

\- `txtSourcePath.Value` → e.g., `/Documents/pdf\_study/src`  

\- `txtOutputFolder.Value` → e.g., `/Documents/pdf\_study/out`  

\- `tglTables.Value`, `tglFigures.Value` (ensure exactly one is true)  

\- `tglToc.Value` (True/False)  

\- `drpPageFormat.Selected.Value` (e.g., `"letter"` or `"A4"`)



\*\*OnSelect\*\* of your action button:

```powerfx

// Enforce exactly one bundle type

If(

&nbsp;   (tglTables.Value \&\& tglFigures.Value) || (!tglTables.Value \&\& !tglFigures.Value),

&nbsp;   Notify("Select either Tables or Figures (not both).", NotificationType.Error);

&nbsp;   ResetFocus(Self); // abort

&nbsp;   Return()

);



// Call cloud flow

UpdateContext({locBusy: true});

Set(

&nbsp;   varResult,

&nbsp;   Flow\_AddPdfToc\_Cloud.Run(

&nbsp;       {

&nbsp;           sourcePath: Trim(txtSourcePath.Value),

&nbsp;           outputFolder: Trim(txtOutputFolder.Value),

&nbsp;           tables: tglTables.Value,

&nbsp;           figures: tglFigures.Value,

&nbsp;           toc: tglToc.Value,

&nbsp;           pageFormat: drpPageFormat.Selected.Value

&nbsp;       }

&nbsp;   )

);



// UI feedback

If(

&nbsp;   Lower(Coalesce(varResult.status, "")) = "ok",

&nbsp;   Notify("Bundle created", NotificationType.Success),

&nbsp;   Notify("Error: " \& Coalesce(varResult.error, "Unknown error"), NotificationType.Error)

);



UpdateContext({locBusy: false});

```



\*\*Open link button\*\*:

```powerfx

btnOpenLink.DisplayMode = If(IsBlank(varResult.shareLink), DisplayMode.Disabled, DisplayMode.Edit);

btnOpenLink.OnSelect = If(

&nbsp;   !IsBlank(varResult.shareLink),

&nbsp;   Launch(varResult.shareLink),

&nbsp;   Notify("No link to open.", NotificationType.Warning)

);

```



\*\*Labels\*\*:

```powerfx

Label\_Status.Text = Coalesce(varResult.status, "");

Label\_Output.Text = Coalesce(varResult.outputPath, ""); // single bundle

Label\_Error.Text  = Coalesce(varResult.error, "");

```



---



##### **## 4) Cloud flow (Power Automate) – \*\*Flow\_AddPdfToc\_Cloud\*\***



\*\*Trigger\*\*: \*\*Power Apps (V2)\*\*  

Create these \*\*Ask in Power Apps\*\* inputs (names exactly):

\- `sourcePath` (Text) – e.g., `/Documents/pdf\_study/src`

\- `outputFolder` (Text) – e.g., `/Documents/pdf\_study/out`

\- `tables` (Yes/No)

\- `figures` (Yes/No)

\- `toc` (Yes/No)

\- `pageFormat` (Text) – default `"letter"`



\*\*Step A – Validate single-bundle choice\*\* (Compose or Condition)

\- Condition: `(tables AND figures) OR (NOT tables AND NOT figures)`

&nbsp; - If \*\*true\*\* → \*\*Respond to Power App\*\* with error:

&nbsp;   ```json

&nbsp;   {

&nbsp;     "status": "ERROR",

&nbsp;     "outputPath": "",

&nbsp;     "shareLink": "",

&nbsp;     "error": "Select either Tables or Figures (not both)."

&nbsp;   }

&nbsp;   ```

&nbsp; - If \*\*false\*\* → continue.



\*\*Step B – Run a desktop flow\*\*  

Action: \*\*Run a flow built with Power Automate for desktop\*\*  

Pass the six inputs directly:

\- `sourcePath`, `outputFolder`, `tables`, `figures`, `toc`, `pageFormat`



Expect \*\*outputs from PAD\*\*:

\- `status` (Text)

\- `outLocalPaths` (Array of Text; we’ll only get 1 for single bundle)

\- `stdout` (Text), `stderr` (Text), `error` (Text)



\*\*Step C – Wait for OneDrive sync to complete\*\*  

Even though the file is on the synced folder, give OneDrive a moment to upload. Use a \*\*Do until\*\* loop (max 5 iterations, delay 5 s):

1\. \*\*Compose – local path\*\* = `first(outputs('Run\_a\_desktop\_flow')?\['body/outLocalPaths'])`

2\. Derive the \*\*server path\*\* (reuse `outputFolder` + file name). We’ll build it after we know the file name (below).

3\. Inside loop:

&nbsp;  - \*\*Get file metadata using path\*\* (SharePoint)

&nbsp;  - If 200 OK, \*\*Exit loop\*\*; else \*\*Delay 5 seconds\*\* and retry.



\*\*Step D – Compute server path + Create sharing link\*\*

1\. \*\*Compose – file name\*\* from local path (substring after last `\\`).

2\. \*\*Compose – server path\*\* = `concat(outputs('triggerBody')?\['outputFolder'], '/', outputs('Compose\_-\_file\_name'))`

&nbsp;  - Example: `/Documents/pdf\_study/out/\_merged\_tables.pdf`

3\. \*\*Create sharing link for a file\*\* (SharePoint):

&nbsp;  - Site: your site

&nbsp;  - File Path: \*\*server path\*\* from step 2

&nbsp;  - Link Type: \*\*View\*\* (or as you prefer)

&nbsp;  - Capture `webUrl`.



\*\*Step E – Respond to Power Apps\*\*  

Use \*\*Respond to a Power App or flow\*\* with this object:



```json

{

&nbsp; "status": "@{outputs('Run\_a\_desktop\_flow')?\['body/status']}",

&nbsp; "outputPath": "@{outputs('Compose\_-\_server\_path')}",

&nbsp; "shareLink": "@{outputs('Create\_sharing\_link\_for\_a\_file')?\['body/link/webUrl']}",

&nbsp; "error": "@{coalesce(outputs('Run\_a\_desktop\_flow')?\['body/error'], outputs('Run\_a\_desktop\_flow')?\['body/stderr'], '')}"

}

```



> \*\*Note:\*\* For single-bundle mode we return \*\*only\*\* `outputPath` and `shareLink`. Your Canvas screen already binds to these.



\*\*Suggested flow naming\*\*  

\- Flow: `Flow\_AddPdfToc\_Cloud`  

\- Desktop flow: `DF\_RunPython\_MergePdf\_SingleBundle`



---



##### **## 5) Desktop flow (PAD) – \*\*DF\_RunPython\_MergePdf\_SingleBundle\*\***



\*\*Inputs (Text/Boolean)\*\*  

\- `sourcePath` (Text) – e.g., `/Documents/pdf\_study/src`  

\- `outputFolder` (Text) – e.g., `/Documents/pdf\_study/out`  

\- `tables` (Boolean)  

\- `figures` (Boolean)  

\- `toc` (Boolean)  

\- `pageFormat` (Text)



\*\*Outputs\*\*  

\- `status` (Text) – `"OK"` or `"ERROR"`  

\- `outLocalPaths` (List of Text) – will contain exactly \*\*one\*\* element in single-bundle mode  

\- `stdout` (Text)  

\- `stderr` (Text)  

\- `error` (Text)



\*\*Variables to create inside PAD\*\*  

\- `localSyncRoot` (Text) – paste your actual path, e.g.:  

&nbsp; `C:\\Users\\<you>\\Contoso\\Shared Documents`

\- `localSrc`  (Text) = `%localSyncRoot%%sourcePath%`  

\- `localOut`  (Text) = `%localSyncRoot%%outputFolder%`  

\- `pyExe`     (Text) = path to Python (if needed), e.g. `C:\\Python311\\python.exe` (or just `python`)

\- `pyScript`  (Text) = `C:\\apps\\pdfbundle\\merge\_pdfs.py`

\- `cmd`       (Text) – will be constructed



\*\*Actions (sequence)\*\*



1\) \*\*Create folder\*\* (if not exists): `%localOut%`  

2\) \*\*Build the command\*\* (Set Variable → `cmd`):  

&nbsp;  Base:

&nbsp;  ```

&nbsp;  "%pyExe%" "%pyScript%" -s "%localSrc%" -o "%localOut%\\\_merged.pdf" --page-format %pageFormat%

&nbsp;  ```

&nbsp;  Append flags:

&nbsp;  - If `toc` = true → append ` --toc`

&nbsp;  - If `tables` = true → append ` --tables`

&nbsp;  - If `figures` = true → append ` --figures`



&nbsp;  > Because you selected single-bundle mode, \*\*exactly one\*\* of `--tables` or `--figures` will be appended.



3\) \*\*Run application\*\* (or \*\*Run DOS command / PowerShell\*\*)  

&nbsp;  - File to run: `cmd.exe`  

&nbsp;  - Arguments: `/C ` + `%cmd%`  

&nbsp;  - Capture \*\*Standard output\*\* → variable `stdout`  

&nbsp;  - Capture \*\*Standard error\*\* → variable `stderr`  

&nbsp;  - Capture \*\*Exit code\*\* → variable `exitCode`



4\) \*\*Parse `stdout` for Created:\*\*  

&nbsp;  - Add a \*\*For each\*\* over lines in `stdout` (split on CR/LF).  

&nbsp;  - If line starts with `"Created: "` then  

&nbsp;    - `outFile = SubText(line, 9)` (substring after `"Created: "`)  

&nbsp;    - Add `outFile` to list variable `outLocalPaths`.



5\) \*\*Set status\*\*  

&nbsp;  - If `Count(outLocalPaths) = 1` and `exitCode = 0` → `status = "OK"`  

&nbsp;  - Else → `status = "ERROR"` and set `error = stderr` (or a friendly message if `stderr` blank).



6\) \*\*Return outputs\*\* to cloud flow\*\*  

&nbsp;  - `status`, `outLocalPaths`, `stdout`, `stderr`, `error`.



\*\*Example command strings that PAD will generate\*\*

\- \*\*Tables + TOC (letter)\*\*  

&nbsp; ```cmd

&nbsp; "C:\\Python311\\python.exe" "C:\\apps\\pdfbundle\\merge\_pdfs.py" -s "C:\\Users\\<you>\\Contoso\\Shared Documents\\pdf\_study\\src" -o "C:\\Users\\<you>\\Contoso\\Shared Documents\\pdf\_study\\out\\\_merged.pdf" --page-format letter --toc --tables

&nbsp; ```

\- \*\*Figures + TOC (A4)\*\*  

&nbsp; ```cmd

&nbsp; "C:\\Python311\\python.exe" "C:\\apps\\pdfbundle\\merge\_pdfs.py" -s "C:\\Users\\<you>\\Contoso\\Shared Documents\\pdf\_study\\src" -o "C:\\Users\\<you>\\Contoso\\Shared Documents\\pdf\_study\\out\\\_merged.pdf" --page-format A4 --toc --figures

&nbsp; ```



> Your script will write one file and print `Created: <full local path>` which we parse.



---



##### **## 6) End‑to‑end test**



1\) In SharePoint, put a few PDFs under `/Documents/pdf\_study/src` with `t\_` or `f\_` prefixes as needed.

2\) In the Canvas app, set:

&nbsp;  - `txtSourcePath.Value = /Documents/pdf\_study/src`

&nbsp;  - `txtOutputFolder.Value = /Documents/pdf\_study/out`

&nbsp;  - Toggle \*\*Tables\*\* (on), \*\*Figures\*\* (off), \*\*TOC\*\* (on), Page format \*\*letter\*\*.

3\) Tap the button.  

4\) In a few seconds, you should see:

&nbsp;  - \*\*Status\*\*: `OK`

&nbsp;  - \*\*Output\*\*: `/Documents/pdf\_study/out/\_merged\_tables.pdf` (or `\_merged\_figures.pdf`)

&nbsp;  - \*\*Open PDF\*\* button launches the \*\*share link\*\*.



---



##### **## 7) Troubleshooting tips**



\- \*\*Both toggles on/off\*\* → Cloud flow returns a friendly error (your app shows it).  

\- \*\*No Created:\*\* in stdout → check script/libraries and ensure the input folder has matching prefixes. Also check that the output base `\\\_merged.pdf` is allowed; your script will rename to `\_merged\_tables.pdf`/`\_merged\_figures.pdf`.  

\- \*\*Sync delay\*\* → The Do‑until loop with `Get file metadata using path` handles typical delays. Increase retries/delay if needed.  

\- \*\*Paths with spaces\*\* → We quote every path in the PAD command.  

\- \*\*Permissions\*\* → Creating a sharing link requires appropriate SharePoint permissions.



---



\## 8) Optional niceties



\- Add `stdout`/`stderr` to the \*\*Respond\*\* payload behind a feature flag (for debug screens).  

\- Add a dropdown in Power Apps for bundle type (`"tables"`/`"figures"`) and compute booleans in the cloud flow—purely cosmetic.



---



If you’d like, I can \*\*generate a small Word/PDF handoff\*\* with screenshots for each cloud/PAD step or supply \*\*exportable\*\* flow JSON outlines (you’d still import and bind the PAD connection). Also, if you share your exact \*\*`localSyncRoot`\*\* and \*\*site/library name\*\*, I’ll plug them into the PAD variables and the cloud flow expressions so you can paste everything verbatim.

