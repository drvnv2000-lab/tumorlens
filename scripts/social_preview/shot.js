// Renders docs/social-preview.png (1280x640, GitHub social preview) from social-preview.html.
// Usage: node scripts/social_preview/shot.js "$PWD/scripts/social_preview/social-preview.html" docs/social-preview.png
// The tumour outline is synthetic; no patient data is used.
const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1280,height:640},deviceScaleFactor:1});
await p.goto('file://'+process.argv[2]);await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(800);
await p.screenshot({path:process.argv[3]});await b.close()})();
