'use strict';
// Appearance, decorative vector artwork and Chinese/English interface text.
// Preferences are supplied by the local server, independent of its random port.
window.UsageAppearance = (() => {
  const root = document.documentElement;
  const themes = {
    lavender: {name:'薰衣草紫', note:'薰衣草 · 轻雾', hue:249, saturation:35, accent:'#B7B4DD'},
    ink: {name:'古风黑', note:'竹影 · 飞鸟', hue:42, saturation:7, accent:'#A4A39C'},
    sakura: {name:'樱花粉', note:'樱树 · 落花', hue:337, saturation:48, accent:'#E9B4C8'},
    maple: {name:'枫叶红', note:'落叶 · 凤凰', hue:7, saturation:48, accent:'#CD8B80'},
    glacier: {name:'冰川蓝', note:'冰川 · 薄雾', hue:201, saturation:46, accent:'#A0CADF'},
    meadow: {name:'草原绿', note:'青草 · 微风', hue:102, saturation:32, accent:'#B4CDA8'}
  };
  const artwork = {
    lavender: `<g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M100 300Q95 200 126 100M148 310Q140 200 169 75M190 320Q175 225 213 135M239 315Q229 210 261 96M277 326Q265 230 302 150"/></g><g fill="currentColor">${[[126,100],[169,75],[213,135],[261,96],[302,150]].map(([x,y])=>Array.from({length:7},(_,i)=>`<ellipse cx="${x+(i%2?5:-5)-i*.9}" cy="${y+i*8}" rx="6" ry="9" transform="rotate(${i%2?35:-35} ${x-i*.9} ${y+i*8})"/>`).join('')).join('')}<path d="M106 250q-40-30-25-40 30 6 25 40M155 241q35-40 43-20-13 27-43 20M238 255q-36-32-30-43 30 10 30 43"/></g>`,
    ink: `<g fill="none" stroke="currentColor" stroke-linecap="round"><path d="M92 340Q100 190 75 30M183 352Q155 200 202 15M282 345Q258 210 303 72" stroke-width="5"/><path d="m86 112 19-3m-14 65 19-3m-12 66 16-2m64-130 19 3m-28 54 18 4m-18 60 18 3m93-65 18 2m-26 54 17 3" stroke-width="3"/><path d="M115 145Q150 120 173 128M190 86Q229 45 266 52M272 213Q312 177 348 186" stroke-width="2"/><path d="M295 53q13-15 25 0 14-13 27-4M330 84q10-12 20 0 10-10 21-4M240 31q9-9 18 0 9-9 18-4" stroke-width="2"/></g><g fill="currentColor"><path d="M111 144q12-40 25-43-3 33-25 43M128 134q34-9 47 0-26 10-47 0M147 128q5-29 19-36 1 29-19 36M199 77q8-35 23-39-1 25-23 39M221 60q25 7 29 21-21-3-29-21M240 53q21-19 31-13-8 17-31 13M275 209q-4-35 8-45 10 26-8 45M296 193q29 1 37 14-25 4-37-14M321 185q17-25 29-22-3 22-29 22"/></g>`,
    sakura: `<g fill="none" stroke="currentColor" stroke-linecap="round"><path d="M275 345Q245 262 264 171 272 103 211 55M261 185Q195 146 152 83M263 159Q321 124 343 66M255 235Q197 205 159 182" stroke-width="8"/><path d="m208 143-16-56m99 51 15-55M225 75l21-32m68 70 44-6M201 211l-23-45" stroke-width="3"/></g><g fill="currentColor">${[[211,55],[152,83],[343,66],[192,87],[246,43],[306,83],[358,107],[178,166],[159,182],[223,107],[317,128]].map(([x,y])=>`<g transform="translate(${x} ${y})">${Array.from({length:5},(_,i)=>`<ellipse cy="-7" rx="5" ry="8" transform="rotate(${i*72})"/>`).join('')}</g>`).join('')}<ellipse cx="107" cy="221" rx="4" ry="8" transform="rotate(35 107 221)"/><ellipse cx="178" cy="276" rx="4" ry="8" transform="rotate(-25 178 276)"/><ellipse cx="327" cy="248" rx="4" ry="8" transform="rotate(65 327 248)"/><ellipse cx="231" cy="310" rx="4" ry="8"/></g>`,
    maple: `<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M201 179q19-24 33-10 9 14-9 30-17 18-5 36M227 179q45-79 117-56-38 1-61 40 38-17 72-10-49 10-78 49M210 183q-51-61-105-36 37 0 59 31-34-10-63 4 47 1 77 29M223 223q57 10 71 54-34-38-65-27 55 34 40 70-17-40-53-46 24 46-6 72 9-49-18-76-11 43-46 47 35-30 27-68" stroke-width="3"/><path d="m236 165 10-3-5 9M196 227q-14 14-20 24" stroke-width="2"/></g><g fill="currentColor">${[[91,71,-25],[300,47,28],[345,268,-15],[101,285,40]].map(([x,y,r])=>`<path transform="translate(${x} ${y}) rotate(${r})" d="m0-23 5 13 8-5-2 11 11-1-7 10 5 4-17 5-3 14-2-14-17-4 5-5-7-10 11 1-2-11 8 5Z"/>`).join('')}</g>`,
    glacier: `<g fill="currentColor" fill-opacity=".65"><path d="m45 287 84-165 53 78 57-143 105 222Z"/><path d="m122 310 87-129 46 60 37-86 78 154Z" fill-opacity=".5"/></g><g fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="m45 287 84-165 53 78 57-143 105 222M95 189l34-67 22 86 31-8 57-143-5 119 29-24 29 40M105 310l104-129 46 60 37-86 78 154M209 181l-7 68 18-12 35 4m37-86-7 101 26-23 26 18M50 322q110-16 201 2t120-1M75 342q85-8 160 0t109 0"/></g>`,
    meadow: `<g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M29 315q153-37 350-5M88 318Q85 208 45 177m43 141q10-96 64-134M140 309q-10-134-58-175m58 175q16-113 63-177M207 307q-6-122-50-162m50 162q18-106 61-142M270 313q-2-109-43-150m43 150q28-115 76-162M332 321q-15-85-38-107m38 107q8-76 40-107"/></g><g fill="currentColor"><path d="M86 270q-48-53-40-71 33 19 40 71M107 250q17-49 39-50-8 31-39 50M168 260q-6-50-28-65-1 38 28 65M222 248q15-54 39-53-6 34-39 53M275 273q-39-51-32-72 29 22 32 72M302 256q29-58 46-57-5 34-46 57"/></g>`
  };
  let preferences;
  try {preferences=JSON.parse(root.dataset.preferences)} catch {preferences={}}
  preferences={language:'zh-CN',background:'light',theme:'lavender',...preferences};
  if(!themes[preferences.theme])preferences.theme='lavender';
  const palette=[];
  function svg(theme) {return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 360" fill="none" style="color:${themes[theme].accent}">${artwork[theme]}</svg>`}
  function apply() {
    const theme=themes[preferences.theme],dark=preferences.background==='dark',h=theme.hue,s=theme.saturation;
    root.dataset.theme=preferences.theme;root.dataset.background=preferences.background;root.lang=preferences.language;
    const tone=(lightness,saturation=s)=>`hsl(${h} ${saturation}% ${lightness}%)`;
    const vars={bg:tone(dark?9:97,Math.round(s*.35)),surface:tone(dark?14:100,Math.round(s*.2)),
      'surface-soft':tone(dark?18:97,Math.round(s*.32)),'surface-glass':`hsl(${h} ${Math.round(s*.2)}% ${dark?14:100}% / .93)`,
      ink:tone(dark?91:22,20),muted:tone(dark?67:47,12),line:tone(dark?27:90,Math.round(s*.3)),
      accent:theme.accent,'accent-ink':tone(dark?78:39,Math.max(7,s)),light:tone(dark?23:94,Math.round(s*.65)),
      'chart-empty':tone(dark?21:95,Math.round(s*.3)),'chart-low':tone(dark?34:88,Math.round(s*.65)),
      'chart-mid':tone(dark?68:62,s),'chart-high':tone(dark?82:43,s),
      'motif':`url("data:image/svg+xml,${encodeURIComponent(svg(preferences.theme))}")`};
    for(const [key,value] of Object.entries(vars))root.style.setProperty('--'+key,value);
    root.style.colorScheme=dark?'dark':'light';
    palette.splice(0,palette.length,theme.accent,tone(dark?69:54,s),tone(70,(s+15)%65+10),
      `hsl(${(h+55)%360} 30% ${dark?68:64}%)`,`hsl(${(h+120)%360} 26% 65%)`,`hsl(${(h+210)%360} 30% 66%)`,tone(65,8));
    if(document.body){
      const language=document.getElementById('ui-language');if(language)language.value=preferences.language;
      document.querySelectorAll('[data-background]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.background===preferences.background)));
      document.querySelectorAll('[data-theme-choice]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.themeChoice===preferences.theme)));
      localize(document.body);
      window.dispatchEvent(new Event('usage-appearance-change'));
    }
  }
  const dictionary={
    'UsageDesk · 用量工作台':'UsageDesk · Usage dashboard','用量工作台':'Usage dashboard',
    '看清每一份输入、输出与消耗。':'A clear view of every input, output and cost.',
    '消耗概览':'Overview','可视化图表':'Charts','消耗细则':'Details','消耗趋势':'Usage trends',
    '设置':'Settings','设置页面':'Settings pages','通用设置':'General','数据与价格':'Data & pricing','关闭':'Close',
    '语言':'Language','选择界面显示语言':'Choose your interface language','中文（默认）':'中文 (default)',
    '背景':'Background','浅色或深色，随时切换':'Switch between light and dark',
    '浅色':'Light','深色':'Dark','风格':'Theme','淡淡的色彩，朦胧的图案':'Soft colors, subtle scenery',
    '薰衣草紫':'Lavender','古风黑':'Ink wash','樱花粉':'Cherry blossom','枫叶红':'Maple red','冰川蓝':'Glacier blue','草原绿':'Meadow green',
    '薰衣草 · 轻雾':'Lavender · mist','竹影 · 飞鸟':'Bamboo · birds','樱树 · 落花':'Cherry tree · petals',
    '落叶 · 凤凰':'Leaves · phoenix','冰川 · 薄雾':'Glaciers · mist','青草 · 微风':'Grass · breeze',
    '更改立即生效并自动保存':'Changes apply immediately and save automatically','正在保存…':'Saving…','已保存':'Saved','重试保存':'Retry save',
    '本地只读统计':'Local, read-only analytics','退出程序':'Quit','刷新数据':'Refresh','来源':'Source','项目':'Project','模型':'Model',
    '全部来源':'All sources','全部项目':'All projects','全部模型':'All models','时区':'Time zone','UTC+08:00 中国':'UTC+08:00 China','系统时区':'System time zone',
    '正在读取本地记录…':'Reading local records…','正在读取用量记录…':'Reading usage records…','正在统计…':'Calculating…',
    '读取失败，保留上次数据':'Could not load data; showing previous results','重置所有筛选':'Reset filters',
    '本日':'Today','本周':'This week','本月':'This month','最近一次会话':'Latest session','周一至今':'Since Monday','整段会话':'Full session',
    '缓存输入':'Cached input','非缓存输入':'Uncached input','推理输出':'Reasoning output','一般输出':'Regular output',
    '一般 / 未拆分输出':'Regular / unsplit output','一般 / 未拆分':'Regular / unsplit','输入':'Input','输出':'Output','USD 估算':'USD estimate',
    '暂无会话':'No sessions yet','未定价':'Unpriced','从':'From','至':'To','全部日期':'All dates','近一天':'Last day','近 7 天':'Last 7 days','近 30 天':'Last 30 days','按所选时区统计今天':'Today in the selected time zone',
    'Token 日历热力图':'Token activity calendar','每日消耗 · 柱状图':'Daily usage · bars','消耗走势 · 曲线图':'Daily usage · trend',
    '模型分布 · 饼状图':'Model distribution · pie','当前日期范围':'Selected date range','最近 30 个自然日':'Latest 30 calendar days','Token 构成':'Token breakdown',
    '输入 / 输出':'Input / output','图表指标':'Chart metric','USD 费用':'USD cost','已定价 USD':'Priced USD',
    '按模型切分':'Split by model','按缓存切分':'Split by cache','缓存率':'Cache rate','非缓存 / 未拆分输入':'Uncached / unsplit input','部分记录缺少缓存拆分，未显示相应缓存率。':'Cache rates are omitted where cache breakdowns are unavailable.',
    '缓存率 = 缓存输入 / 总输入 Tokens':'Cache rate = cached input / total input tokens',
    '左轴：输入 Tokens · 右轴：缓存率':'Left axis: input tokens · Right axis: cache rate',
    '缓存输入、非缓存输入与缓存率':'Cached input, uncached input and cache rate',
    '少':'Less','多':'More','一':'Mon','四':'Thu','日':'Sun','其他':'Other',
    '当前费用未定价，请补充价格':'No prices available. Add model prices in Settings.',
    '当前范围暂无用量':'No usage in this date range','（仅已拆分部分）':' (reported portion only)',
    '仅展示已定价费用，未定价部分未计入。':'Only priced usage is shown; unpriced usage is excluded.',
    '导出 CSV':'Export CSV','每日':'Daily','每周':'Weekly','每月':'Monthly','项目用量':'Projects','会话用量':'Sessions','模型用量':'Models',
    '日期 / 名称 ↕':'Date / name ↕','会话名称 ↕':'Session name ↕','总 Tokens ↕':'Total tokens ↕','搜索明细…  Ctrl+K':'Search details…  Ctrl+K','搜索当前明细':'Search details',
    '暂无符合条件的记录':'No matching records','上一页':'Previous','下一页':'Next','每页条数':'Rows per page','返回顶部':'Back to top',
    'UsageDesk 1.0 · 数据留在本机':'UsageDesk 1.0 · Your data stays local',
    '每行填写一个路径。所有渠道留空时自动查找。':'Enter one path per line. Leave any channel blank for automatic discovery.',
    'Antigravity 根目录或 conversations 目录':'Antigravity home or conversations directory','Cursor 用量 CSV、数据库或所在目录':'Cursor usage CSV, database or containing directory',
    'DSH 根目录':'DSH home directories','OpenCode 数据目录':'OpenCode data directories','留空自动查找':'Leave blank for automatic discovery',
    'Codex 根目录':'Codex home directories','Claude Code 根目录':'Claude Code home directories',
    '自定义模型价格（JSON，USD / 百万 Tokens）':'Custom model prices (JSON, USD / million tokens)',
    '例：{"你的模型名":{"input":1.5,"cached":0.15,"output":6,"cache_write":1.875}}':'Example: {"your-model":{"input":1.5,"cached":0.15,"output":6,"cache_write":1.875}}',
    '匹配日志中的完整模型名。自定义价格优先，用于中转站或未知模型；未匹配的优先 / Flex 服务等级不套用标准价格。':'Use the exact model name in your logs. Custom prices take precedence. Unknown priority / Flex tiers are not billed at standard rates.',
    '联网更新价格表':'Update prices online','保存并重新统计':'Save & recalculate',
    '仅点击更新时下载 LiteLLM 公开价格表；不会上传会话内容。设置保存在本机 LocalAppData\\UsageDesk。':'Downloads public LiteLLM prices only when requested. No chat content is uploaded. Settings are stored locally in LocalAppData\\UsageDesk.',
    '有未保存的修改 · Ctrl+Enter 保存':'Unsaved changes · Ctrl+Enter to save','设置已保存，正在重新统计':'Settings saved. Recalculating…',
    '正在下载公开价格表…':'Downloading public prices…','用量数据已更新':'Usage data refreshed',
    'CSV 已导出，包含当前筛选及搜索结果':'CSV exported with your current filters and search',
    '已重置来源、项目、模型和日期筛选':'Source, project, model and date filters reset',
    'UsageDesk 已退出，可以关闭此窗口。':'UsageDesk has stopped. You may close this window.',
    '包含未报告推理拆分的 Claude 记录，仅显示已知部分':'Includes Claude records without reasoning breakdown; only known reasoning is shown',
    '图表可悬停查看数值。':'Hover over charts for values.',
    ' · 含未定价记录':' · includes unpriced usage',
    '开始日期不能晚于结束日期':'Start date must not be after end date','时区超出范围':'Time zone is out of range',
    '无效报表维度':'Invalid report dimension','上游价格表格式无效':'Invalid upstream price table',
    '读取失败，请检查日志 UsageDesk/app.log':'Could not load data. Check UsageDesk/app.log',
    '请求验证失败':'Request verification failed','请求过大':'Request is too large',
    '单价必须是大于等于 0 的有限数字，单位 USD / 百万 Tokens':'Prices must be finite, nonnegative numbers in USD per million tokens'
  };
  const textSources=new WeakMap(),attributeSources=new WeakMap();
  function english(source) {
    const trimmed=source.trim();
    if(dictionary[trimmed])return source.replace(trimmed,dictionary[trimmed]);
    return source
      .replace(/^更新于 /,'Updated at ')
      .replace(/^缓存率：/,'Cache rate: ')
      .replace(' · 缓存输入 · ',' · Cached input · ')
      .replace(' · 非缓存输入 · ',' · Uncached input · ')
      .replace(' · 缓存率 · ',' · Cache rate · ')
      .replace(/ · 每 (\d+) 天汇总/,' · $1-day totals')
      .replace(/^价格快照：(.+?)。/,'Price snapshot: $1. ')
      .replace('已匹配当前范围所有记录的价格。','All selected records have matching prices.')
      .replace(' 当前范围未定价模型 / 服务等级：',' Unpriced models / service tiers: ')
      .replace('。可在设置中补充单价。','. Add prices in Settings.')
      .replace(' 部分分叉缺少父会话，无法核对继承历史。',' Some forks have no parent logs; inherited history cannot be verified.')
      .replace(/^已扫描 (.+?) 个文件 · (.+?) 行无效或未完成记录 · (.+?) 个文件读取失败/,'Scanned $1 files · $2 invalid or incomplete lines · $3 unreadable files')
      .replace(/ · 已剔除 (.+?) 条分叉重放/,' · skipped $1 replayed fork records')
      .replace(' · 部分来源目录不存在',' · some source directories are missing')
      .replace(/^已启用 (.+?) 项筛选 · 共 (.+?) 条用量记录/,'$1 active filters · $2 usage records')
      .replace(/^全部本地记录 · (.+?) 条用量记录/,'All local records · $1 usage records')
      .replace(/^共 (.+?) 条 · 当前范围 (.+?) Tokens/,'$1 rows · $2 tokens in range')
      .replace(/^(.+?) 个活跃日 · /,'$1 active days · ')
      .replace(/^已更新 (.+?) 个价格条目/,'Updated $1 price entries')
      .replace(/^更新失败，保留原价格表：/,'Update failed; previous prices kept: ')
      .replace(/^保存失败：/,'Could not save: ')
      .replace(/^导出失败：/,'Could not export: ')
      .replace(/^无效界面选项：/,'Invalid appearance option: ')
      .replace(/ 应为目录字符串数组，最多 20 个/,' must be a list of up to 20 directory paths')
      .replace(/ 需要 input、cached、output 单价/,' requires input, cached and output prices')
      .replace('prices 应为对象','prices must be an object')
      .replace('单价必须是大于等于 0 的有限数字，单位 USD / 百万 Tokens','Prices must be finite, nonnegative numbers in USD per million tokens')
      .replace('未定价 Tokens：','Unpriced tokens: ')
      .replace(' · 含未定价记录',' · includes unpriced usage')
      .replace(' + 未定价',' + unpriced')
      .replace(/^(\d{1,2})月$/,(_,n)=>['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][Number(n)-1]);
  }
  function excluded(element) {
    return !element||element.closest('script,style,textarea,[data-no-i18n],#project option,#model option,#source option:not([value=""]),.legend-name,td:first-child');
  }
  function localize(container) {
    if(!container)return;
    const walker=document.createTreeWalker(container,NodeFilter.SHOW_TEXT);
    let node;
    while((node=walker.nextNode())) {
      if(excluded(node.parentElement)||!node.nodeValue.trim())continue;
      const previous=textSources.get(node);
      const source=previous&&node.nodeValue===previous.output?previous.source:node.nodeValue;
      const output=preferences.language==='en'?english(source):source;
      textSources.set(node,{source,output});
      if(node.nodeValue!==output)node.nodeValue=output;
    }
    for(const element of container.querySelectorAll('[title],[placeholder],[aria-label]')) {
      if(excluded(element)&&!element.matches('textarea[data-path-setting]'))continue;
      const stored=attributeSources.get(element)||{};
      for(const name of ['title','placeholder','aria-label']) {
        if(!element.hasAttribute(name))continue;
        const value=element.getAttribute(name),previous=stored[name];
        const source=previous&&value===previous.output?previous.source:value;
        const output=preferences.language==='en'?english(source):source;
        stored[name]={source,output};
        if(value!==output)element.setAttribute(name,output);
      }
      attributeSources.set(element,stored);
    }
    document.title=preferences.language==='en'?'UsageDesk · Usage dashboard':'UsageDesk · 用量工作台';
  }
  let saving=false,revision=0,savedRevision=0;
  async function persist() {
    if(saving)return;
    saving=true;
    const status=document.getElementById('general-status'),retry=document.getElementById('retry-preferences');
    retry.hidden=true;
    try {
      while(savedRevision<revision) {
        const current=revision;
        status.textContent='正在保存…';
        const response=await fetch('/api/preferences',{method:'POST',headers:{'Content-Type':'application/json','X-Usage-Token':document.querySelector('meta[name=usage-token]').content},body:JSON.stringify(preferences)});
        const result=await response.json();if(!response.ok)throw Error(result.error||`HTTP ${response.status}`);
        savedRevision=current;
      }
      status.textContent='已保存';
    } catch(error) {status.textContent='保存失败：'+error.message;retry.hidden=false}
    finally {saving=false;localize(document.body)}
  }
  function change(key,value) {preferences={...preferences,[key]:value};apply();revision++;persist()}
  function showPage(name) {
    for(const id of ['general','data']) {
      const selected=id===name;
      document.getElementById(id+'-panel').hidden=!selected;
      document.getElementById(id+'-tab').setAttribute('aria-selected',String(selected));
      document.getElementById(id+'-tab').tabIndex=selected?0:-1;
    }
  }
  apply();
  document.addEventListener('DOMContentLoaded',()=>{
    const options=document.getElementById('theme-options');
    options.innerHTML=Object.entries(themes).map(([id,theme])=>`<button type="button" class="theme-choice" data-theme-choice="${id}" aria-pressed="false"><span class="theme-preview" style="--preview-hue:${theme.hue};--preview-accent:${theme.accent}" aria-hidden="true">${svg(id)}<i></i><i></i><i></i></span><span class="theme-name">${theme.name}</span><span class="theme-note">${theme.note}</span><span class="theme-check" aria-hidden="true">✓</span></button>`).join('');
    document.getElementById('ui-language').onchange=e=>change('language',e.target.value);
    document.querySelectorAll('[data-background]').forEach(button=>button.onclick=()=>change('background',button.dataset.background));
    options.onclick=e=>{const button=e.target.closest('[data-theme-choice]');if(button)change('theme',button.dataset.themeChoice)};
    document.getElementById('retry-preferences').onclick=persist;
    for(const name of ['general','data']) {
      const tab=document.getElementById(name+'-tab');tab.onclick=()=>showPage(name);
      tab.onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?'general':e.key==='End'?'data':name==='general'?'data':'general';showPage(next);document.getElementById(next+'-tab').focus()}};
    }
    let queued=false;
    new MutationObserver(()=>{if(!queued){queued=true;queueMicrotask(()=>{queued=false;localize(document.body)})}}).observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['title','placeholder','aria-label']});
    apply();showPage('general');
  });
  return {palette,showPage,localize,get preferences(){return {...preferences}}};
})();
