const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const bootstrap=fs.readFileSync(path.join(root,'templates/partials/theme_head.html'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const runtime=fs.readFileSync(path.join(root,'static/js/theme.js'),'utf8');
for(const saved of [null,'dark','light','invalid'])for(const blocked of [false,true]){
 const handlers={},attrs={},label={},icon={classList:{contains:()=>false}},element={dataset:{},style:{}};
 let stored=saved;
 const button={setAttribute:(k,v)=>attrs[k]=v,querySelector:s=>s.includes('label')?label:icon};
 const document={documentElement:element,querySelectorAll:()=>[button],addEventListener:(k,f)=>handlers[k]=f,dispatchEvent:e=>handlers[e.type]?.(e)};
 const context={document,localStorage:{getItem(){if(blocked)throw Error();return stored;},setItem(k,v){if(blocked)throw Error();stored=v;}},CustomEvent:class{constructor(type,options){this.type=type;this.detail=options.detail;}},getComputedStyle:()=>({getPropertyValue:n=>n+'-'+element.dataset.theme})};
 context.window=context;context.addEventListener=(k,f)=>handlers[k]=f;
 vm.createContext(context);vm.runInContext(bootstrap,context);vm.runInContext(runtime,context);
 const initial=!blocked&&saved==='light'?'light':'dark';
 assert.equal(element.dataset.theme,initial);
 handlers.DOMContentLoaded();assert.equal(attrs['aria-pressed'],String(initial==='dark'));
 context.SRTheme.toggle();assert.equal(element.dataset.theme,initial==='dark'?'light':'dark');
 assert.equal(attrs['aria-label'],'Tema oscuro');
 if(!blocked)assert.equal(stored,element.dataset.theme);
 handlers.storage({key:'theme',newValue:'light'});assert.equal(element.dataset.theme,'light');
 handlers.storage({key:'theme',newValue:'nonsense'});assert.equal(element.dataset.theme,'dark');
 let plugin,updates=0;
 context.Chart={register:p=>plugin=p,instances:{one:{update:mode=>{assert.equal(mode,'none');updates++;}}}};
 vm.runInContext(fs.readFileSync(path.join(root,'static/js/theme-charts.js'),'utf8'),context);
 const chart={options:{plugins:{legend:{labels:{}},tooltip:{}},scales:{x:{ticks:{},grid:{},title:{}}}},data:{labels:['A','B'],datasets:[{}]},config:{type:'doughnut'}};
 plugin.beforeUpdate(chart);assert.equal(chart.data.datasets[0].backgroundColor.length,2);
 context.SRTheme.set('light');assert.equal(updates,1);
 plugin.beforeUpdate(chart);assert.equal(chart.options.color,'--theme-text-light');
}
console.log('Theme bootstrap, preference, accessibility, blocked storage, cross-tab sync and chart refresh: passed.');
