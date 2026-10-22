const {run}=require('/tmp/w5-baseline-harness.cjs')
run('pr440-fonts',async({as,check,shot})=>{
 const page=await as('admin',{fresh:true})
 const fonts=await page.evaluate(async()=>{await document.fonts.ready;return Array.from(document.fonts).filter(f=>f.family.includes('IBM Plex')).map(f=>({family:f.family,status:f.status,weight:f.weight}))})
 check('IBM Plex Sans actually loaded',fonts.some(f=>f.family.includes('Sans')&&f.status==='loaded'),JSON.stringify(fonts))
 await shot(page,'pr440-fonts-loaded')
})
