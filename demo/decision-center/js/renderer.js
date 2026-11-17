import { loadDecisionObject } from './loader.js';
const mode = document.getElementById('useCase');
const scenario = document.getElementById('standbyScenario');
const result = document.getElementById('standbyResult');
const status = document.getElementById('standbyStatus');
let revision = 0;
const node = (tag, text) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; return n; };
const fmt = (v, unit) => v == null ? 'Unknown / not assessed' : `${v.toFixed(2)} ${unit}`;
const state = v => v == null ? 'No recommendation' : v.replaceAll('_', ' ');
function panel(title, parent) { const p = node('article'); p.className = 'panel'; p.append(node('h2', title)); parent.append(p); return p; }
function table(p, headers, rows) { const w=node('div'); w.className='standby-scroll'; const t=node('table'); t.className='standby-table'; const head=node('thead'); const h=node('tr'); headers.forEach(x=>{const th=node('th',x); th.scope='col'; h.append(th);}); head.append(h); t.append(head); const b=node('tbody'); rows.forEach(row=>{const r=node('tr');row.forEach(x=>r.append(node('td',x))); b.append(r);}); t.append(b); w.append(t); p.append(w); }
function render(d) {
  if (d.decision_type !== 'ENERGY_AWARE_STANDBY' || d.context?.synthetic !== true || d.governance?.execution_permitted !== false || d.context?.scenario_id !== scenario.value.toUpperCase() || d.alternatives?.length !== 3) throw Error('Unexpected or non-synthetic Decision Object');
  const g=d.governance, o=d.expected_outcome, a=d.alternatives;
  const frag=document.createDocumentFragment();
  const c=panel('Decision context & evidence',frag);
  c.append(node('p',`Assumed analysis horizon: ${d.context.analysis_horizon_min} min (conditional only; not a known restart time).`));
  d.evidence.forEach(e=>c.append(node('p',`${e.field}: ${typeof e.status==='object'?Object.entries(e.status).map(([k,v])=>`${state(k)}: ${v}`).join(' · '):e.status}`)));
  const s=panel('1 · Conditional simulation',frag);
  s.append(node('p',`Preferred among conditionally feasible states: ${state(g.conditional_preferred_state)}. ALLOW here means synthetic scenario feasibility only.`));
  table(s,['State','Energy (kWh)','Energy cost (EUR)','Restart (min)','Scenario feasibility'],a.map(x=>[state(x.state),fmt(x.energy_kwh,'kWh'),fmt(x.energy_cost_eur,'€'),String(x.restart_duration_min),x.scenario_feasibility]));
  s.append(node('p',`Conditional energy saving vs READY: ${fmt(o.conditional_energy_saving_kwh,'kWh')}; avoided energy cost only: ${fmt(o.conditional_avoided_energy_cost_eur,'€')}.`),node('p','Production impact cost and economic net benefit: unknown. No realised savings claimed.'));
  const r=panel('2 · Realtime governance (simulated)',frag);
  r.append(node('p',`State-change gate: ${g.realtime_change_gate}. Baseline status: ${g.baseline_status}. Model recommendation: ${state(g.realtime_recommended_state)}.`),node('p','No physical execution authorized. Human authorization required; this demo cannot provide it.'),node('p',g.reason));
  table(r,['State','Realtime status','Constraint / evidence reasoning'],a.map(x=>[state(x.state),x.realtime_status,x.reasons.join(' · ') || 'Unchanged baseline under synthetic assumptions only.']));
  const raw=panel('Decision Object provenance',frag); raw.append(node('p',`${d.decision_id} · ${d.contract.version} · ${d.timestamp}`)); const details=node('details'); details.append(node('summary','Show raw JSON'),node('pre',JSON.stringify(d,null,2))); raw.append(details);
  result.replaceChildren(frag);
}
async function load() { const token=++revision; result.replaceChildren(); status.textContent='Loading precomputed scenario…'; try { if (!['s01','s02','s03'].includes(scenario.value)) throw Error('Unknown scenario'); const d=await loadDecisionObject(`data/standby/${scenario.value}_result.json`); if(token!==revision)return; render(d); status.textContent='Precomputed scenario loaded.'; } catch(e) { if(token!==revision)return; result.replaceChildren(); status.textContent=`Scenario unavailable: ${e.message}`; } }
mode.addEventListener('change',()=>{const active=mode.value==='standby';document.getElementById('standbyCenter').hidden=!active;document.getElementById('decisionCenter').hidden=active; document.getElementById('reloadButton').hidden=active; if(active)load();else{revision++;result.replaceChildren();status.textContent='';}});
scenario.addEventListener('change',load);
