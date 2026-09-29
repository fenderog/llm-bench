{prompt}

Build this as an interactive web page in the current directory.
- The entry point is index.html. Put your code in JavaScript ES modules loaded from it
  (`<script type="module" src="main.js">`), and add a short README.md.
- You may use npm packages: `npm install <package>` here, then import them by name
  (`import * as THREE from "three"`). No CDN URLs and no import maps.
- Afterwards the page is packaged into one self-contained index.html with esbuild: every script and
  stylesheet index.html references is bundled with everything it imports. Load assets the page needs
  with `import` (they become data URLs) or generate them in code, never by URL string.
- The packaged page runs offline in a sandboxed iframe: no network requests, and no localStorage,
  cookies or other storage (they throw there).
- Check that it packages: `esbuild main.js --bundle --format=esm --outfile=/dev/null` must succeed.
  Don't build or package the page yourself; that happens afterwards.
- Only create or edit files inside the current directory.
- Finish with a short summary of what you built.
