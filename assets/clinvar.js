'use strict';
async function ncbiJson(endpoint, params) {
  const url = new URL(endpoint + '.fcgi','https://eutils.ncbi.nlm.nih.gov/entrez/eutils/');
  url.search = new URLSearchParams({db:'clinvar',retmode:'json',...params});
  const response = await fetch(url,{signal:AbortSignal.timeout(10000)});
  if (!response.ok) throw Error('NCBI 暫時無法連線');
  return response.json();
}
async function resolveClinVar(gene,hgvs) {
  if (!/^[A-Z0-9.-]+$/.test(gene) || !/^[cgnmrp]\.[A-Za-z0-9_+*>?=().-]+$/.test(hgvs))
    return {status:'位點標記待核對'};
  const search = await ncbiJson('esearch',{term:gene+'[gene] AND "'+hgvs+'"',retmax:'40'});
  const result = search.esearchresult;
  if (+result.count>result.idlist.length) return {status:'候選紀錄過多，待核對'};
  if (!result.idlist.length) return {status:'未找到相符的 ClinVar 紀錄'};
  const summary = await ncbiJson('esummary',{id:result.idlist.join(',')});
  const matches=[];
  for (const id of result.idlist) {
    const v=summary.result[id];
    const m=/^((?:NM|NR)_\d+\.\d+)\(([^()]+)\):([^\s]+)(?: \((p\.[^()]+)\))?$/.exec(v?.title || '');
    if (!m || m[2]!==gene || m[3]!==hgvs || !/^VCV\d+\.\d+$/.test(v.accession_version)) continue;
    const traits=(v.germline_classification?.trait_set || []).map(t=>t.trait_name).filter(t=>t && !['not provided','not specified'].includes(t.toLowerCase()));
    matches.push({accession:v.accession,version:v.accession_version,transcript:m[1],protein:m[4]||'',scope:[...new Set(traits)].join('、') || 'ClinVar 未列明疾病',status:'已核對 ClinVar'});
  }
  return matches.length===1 ? matches[0] : {status:matches.length?'多筆相符，待核對':'未找到完全相符的 ClinVar 紀錄'};
}
