// SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
// SPDX-License-Identifier: MIT
// Cron-triggered hourly snapshots of already-sanitized public official provider status.
const SOURCE="https://resoarc.com/api/v1/outages";
const LATEST="outage:latest:v1";
const HEALTH="outage:health:v1";
const JOURNAL="outage:journal:v1";
const RETENTION=30*86400;
const HEADERS=Object.freeze({
  "Content-Type":"application/json; charset=utf-8",
  "Access-Control-Allow-Origin":"*",
  "Cache-Control":"public, max-age=120",
  "X-Content-Type-Options":"nosniff",
  "Content-Security-Policy":"default-src 'none'"
});
const json=(value,status=200,head=false)=>new Response(head?null:JSON.stringify(value),{status,headers:HEADERS});
const expired=(x)=>!x||Date.now()-Date.parse(x)>90*60000;
async function collect(env,kind) {
  const attempt_at=new Date().toISOString();
  let old=await env.OUTAGES.get(LATEST,"json");
  let history=await env.OUTAGES.get(JOURNAL,"json");
  if(!Array.isArray(history))history=[];
  try {
    const res=await fetch(SOURCE,{
      headers:{"Accept":"application/json"},signal:AbortSignal.timeout(16000),cf:{cacheTtl:0}
    });
    if(!res.ok)throw new Error("source_http_"+res.status);
    const current=await res.json();
    if(current.schema_version!=="1.0" || !Array.isArray(current.services) ||
        !Array.isArray(current.incidents) || current.checked_count!==12 ||
        current.incidents.length>250)throw new Error("source_schema_invalid");
    if(current.failed_sources===current.checked_count)
      throw new Error("all_sources_failed");
    const success={...current, collection_mode:"hourly_cron",collected_at:attempt_at,
      last_success_at:attempt_at, collection_interval_minutes:60,
      history_retention_days:30, snapshot_quality:current.quality};
    const entry={collected_at:attempt_at,quality:current.quality,
      checked_count:current.checked_count,failed_sources:current.failed_sources,
      active_incidents:current.active_incidents,recent_incidents:current.recent_incidents};
    history.push(entry);
    history=history.filter(x=>Date.parse(x.collected_at)>=Date.now()-RETENTION*1000).slice(-720);
    await env.OUTAGES.put(LATEST,JSON.stringify(success));
    await env.OUTAGES.put(JOURNAL,JSON.stringify(history));
    await env.OUTAGES.put(HEALTH,JSON.stringify({last_attempt_at:attempt_at,last_success_at:attempt_at,
      last_attempt_status:"success",snapshot_quality:current.quality,collection_trigger:kind}));
    console.log("HOURLY_SUCCESS",JSON.stringify(entry));
    return success;
  }catch(error){
    await env.OUTAGES.put(HEALTH,JSON.stringify({
      last_attempt_at:attempt_at,last_success_at:old&&old.last_success_at||null,
      last_attempt_status:"failed",reason:String(error&&error.message||error).slice(0,120),
      collection_trigger:kind}));
    console.error("HOURLY_FAILURE",String(error&&error.message||error));
    if(old)return old;
    throw error;
  }
}
export default {
  async scheduled(_controller,env,ctx) {
    ctx.waitUntil(collect(env,"scheduled"));
    ctx.waitUntil(collectPhp(env,"scheduled"));
  },
  async fetch(request,env,ctx) {
    const url=new URL(request.url);
    const method=request.method;
    if(url.pathname==="/v1/php/discovery/diagnostics")return phpRssDiagnostics(request);
    if(url.pathname==="/v1/php/discovery/refresh")return phpRefreshDiscovery(request,env);
    if(method==="OPTIONS")return new Response(null,{status:204,headers:HEADERS});
    if(method!=="GET"&&method!=="HEAD")return json({error:"method_not_allowed"},405,method==="HEAD");
    if(url.search||!["/","/v1/outages","/v1/health","/v1/history","/v1/php","/v1/php/history"].includes(url.pathname))
      return json({error:"not_found"},404,method==="HEAD");
    if(url.pathname==="/v1/php/history"){
      const history=await env.OUTAGES.get(PHP_HISTORY,"json");
      return json({schema_version:"1.0",history:Array.isArray(history)?history:[],retention_days:30},200,method==="HEAD");
    }
    if(url.pathname==="/v1/php"){
      let row=await readPhp(env);
      if(row.error){
        try {row=await collectPhp(env,"first_read_bootstrap");}
        catch {return json({quality:"UNAVAILABLE",error:"php_feed_unavailable"},503,method==="HEAD");}
      }
      return json(row,200,method==="HEAD");
    }
    if(url.pathname==="/v1/history"){
      const history=await env.OUTAGES.get(JOURNAL,"json");
      return json({schema_version:"1.0",retention_days:30,history:Array.isArray(history)?history:[]},200,method==="HEAD");
    }
    if(url.pathname==="/v1/health"){
      const h=await env.OUTAGES.get(HEALTH,"json");
      const latest=await env.OUTAGES.get(LATEST,"json");
      return json({...h,snapshot_exists:Boolean(latest),snapshot_stale:expired(latest?.last_success_at)},200,method==="HEAD");
    }
    let latest=await env.OUTAGES.get(LATEST,"json");
    if(!latest){
      // Single one-time initialization, normally later refreshes are Cron-only.
      try {latest=await collect(env,"first_read_bootstrap");}
      catch{return json({error:"hourly_snapshot_unavailable",quality:"UNAVAILABLE"},503,method==="HEAD");}
    }
    const health=await env.OUTAGES.get(HEALTH,"json");
    return json({...latest,last_attempt_at:health?.last_attempt_at||null,
      last_attempt_status:health?.last_attempt_status||"unknown",
      snapshot_stale:expired(latest.last_success_at),
      data_freshness_notice:expired(latest.last_success_at)?"最終収集から90分以上経過しています":null},200,method==="HEAD");
  }
};


/* Corporate PHP incident reports. Each status is attributed to its dated official notice.
   HTTP reachability is a separate signal and MUST NEVER override a service notice. */
const PHP_REGISTRY = [{"id":"buffalo","name":"バッファロー","service":"LinkStation/TeraStation一部更新・FREESPOT等","official_status":"partial","source_url":"https://www.buffalo.jp/news/detail/20261022-01.html","website_url":"https://www.buffalo.jp","source_date":"2026-10-23","note":"対応済みと継続停止が混在","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"tkc","name":"TKC","service":"会計事務所・関与先・自治体向け一部サービス","official_status":"partial","source_url":"https://www.tkc.jp/company/topics/2026/20261023/","website_url":"https://www.tkc.jp","source_date":"2026-10-23","note":"23日：会計事務所向け一部サービスを除いて再開、残存サービスは停止継続","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"plala","name":"BUSINESSぷらら","service":"ビジネスサーバ・Standardプラス Webサービス","official_status":"suspended","source_url":"https://biz.plala.or.jp/support/info/2026/1022-1.html","website_url":"https://biz.plala.or.jp","source_date":"2026-10-23","note":"PHP旧環境の停止・再開準備中","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"cpi","name":"CPI（KDDI系）","service":"サービスサイト・管理画面等","official_status":"partial","source_url":"https://www.cpi.ad.jp/news/support-info/261022/","website_url":"https://www.cpi.ad.jp","source_date":"2026-10-22","note":"順次停止とパッチ適用を発表","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"unverified_primary","verification_date":"2026-10-24"},{"id":"spiderplus","name":"スパイダープラス","service":"SPIDER+、S+Partner等5サービス","official_status":"suspended","source_url":"https://spiderplus.co.jp/news/news-release/9804/","website_url":"https://spiderplus.co.jp","source_date":"2026-10-22","note":"10月22日8時から停止と公表","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"iridge","name":"アイリッジ","service":"コーポレートサイト","official_status":"suspended","source_url":"https://dtys0pdpjhvs4.cloudfront.net/","website_url":"https://iridge.jp","source_date":"2026-10-21","note":"公式代替お知らせ上で一時停止を公表","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"unverified_primary","verification_date":"2026-10-24"},{"id":"mechatrolink","name":"MECHATROLINK協会","service":"協会Webサイト","official_status":"suspended","source_url":"https://www.mechatrolink.org/maintainance/index.html","website_url":"https://www.mechatrolink.org","source_date":"2026-10-22","note":"安全確認まで停止","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"nsd","name":"NSD","service":"ソリューションサイト・一部グループ会社サイト","official_status":"suspended","source_url":"https://www.nsd.co.jp/news/2026/oshirase20261023.html","website_url":"https://www.nsd.co.jp","source_date":"2026-10-23","note":"ホームページ全体が停止しているわけではない","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"nichii","name":"ニチイ学館","service":"ニチイの介護・ニチイライフ・サニーメイド","official_status":"suspended","source_url":"https://www.nichiigakkan.co.jp/topics/2026/1023-1633.html","website_url":"https://www.nichii-kaigo.jp/","source_date":"2026-10-23","note":"対象は一部サービスサイト","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"oitabank","name":"大分銀行","service":"ペンリィ・大分銀行スクエア","official_status":"suspended","source_url":"https://www.oitabank.co.jp/news/article/topics/2026/20261022_001.html","website_url":"https://www.oitabank.co.jp","source_date":"2026-10-23","note":"銀行サイト全体は停止していない","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"genetec","name":"ゼネテック","service":"Mastercam・FlexSimサイト","official_status":"suspended","source_url":"https://www.genetec.co.jp/news/news-261023/","website_url":"https://www.genetec.co.jp","source_date":"2026-10-23","note":"製品サイトの停止、会社サイト全体ではない","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"ibex","name":"IBEXエアラインズ","service":"Apple Wallet搭乗券発行","official_status":"suspended","source_url":"https://www.ibexair.co.jp/information/5d504d4c4f9f91d4d10435e043e6fa869ac13934.html","website_url":"https://www.ibexair.co.jp","source_date":"2026-10-22","note":"予約購入・オンラインチェックインは対象外","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"keishin","name":"大阪府警察信用組合","service":"アプリ・事前審査・住所変更受付","official_status":"suspended","source_url":"https://pop.osaka-keishin.co.jp/information/","website_url":"https://pop.osaka-keishin.co.jp","source_date":"2026-10-22","note":"対象サービスの一時停止","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"minato","name":"東京都港区","service":"公式サイト等の一部機能","official_status":"partial","source_url":"https://www.city.minato.tokyo.jp/houdou/kuse/koho/press/202610/20261022_2.html","website_url":"https://www.city.minato.tokyo.jp","source_date":"2026-10-22","note":"自治体の予防的一時停止","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"nttbp","name":"NTTブロードバンドプラットフォーム","service":"Webサイト","official_status":"restored","source_url":"https://www.ntt-bp.net/articles/2026/10/PHP-Web.html","website_url":"https://www.ntt-bp.net","source_date":"2026-10-22","note":"22日13時ごろ公開再開","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"fcode","name":"エフ・コード","service":"コーポレートサイト","official_status":"restored","source_url":"https://f-code.co.jp/news/news_2178/","website_url":"https://f-code.co.jp","source_date":"2026-10-22","note":"22日14時29分復旧","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"kokopelli","name":"ココペリ","service":"Big Advance・BAポータル等4サービス","official_status":"restored","source_url":"https://www.kokopelli-inc.com/all/7045/","website_url":"https://www.kokopelli-inc.com","source_date":"2026-10-23","note":"23日2時45分までに全対象復旧","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"relay","name":"日本財団電話リレーサービス","service":"電話リレーサービス・手話リンク","official_status":"restored","source_url":"https://www.nftrs.or.jp/news/incident/mt20261022-1","website_url":"https://www.nftrs.or.jp","source_date":"2026-10-23","note":"23日13時ごろ再開","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"hokuriku","name":"北陸銀行","service":"Hokuriku Big Advance・口座振替新規受付","official_status":"restored","source_url":"https://www.hokugin.co.jp/info/important/archives/personal/2026/php_1.html","website_url":"https://www.hokugin.co.jp","source_date":"2026-10-23","note":"23日：対象のHokuriku Big AdvanceとWEB口座振替受付の2機能が再開","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"amone","name":"アセットマネジメントOne","service":"コーポレートサイトの一部サービス","official_status":"restored","source_url":"https://www.am-one.co.jp/company/newsroom/news/524.html","website_url":"https://www.am-one.co.jp","source_date":"2026-10-23","note":"一部サービス再開を公表","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"kimaroom","name":"キマルーム","service":"電子申込・契約等6サービス","official_status":"restored","source_url":"https://www.kimaroom.co.jp/news/1359","website_url":"https://www.kimaroom.co.jp","source_date":"2026-10-23","note":"23日9時に全サービス再開","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"takeei","name":"タケエイ","service":"Webサイト","official_status":"restored","source_url":"https://www.takeei.co.jp/news/2026/20261023.html","website_url":"https://www.takeei.co.jp","source_date":"2026-10-23","note":"23日11時ごろ再開","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"kagoshima","name":"鹿児島銀行","service":"かぎんアプリ通知・Payどん一部機能","official_status":"restored","source_url":"https://www.kagin.co.jp/important/emergency_20261023.html","website_url":"https://www.kagin.co.jp","source_date":"2026-10-23","note":"対象機能の利用再開","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"oitabus","name":"大分バス","service":"会社サイト（一部の運行状況・採用は停止継続）","official_status":"partial","source_url":"https://www.oitabus.co.jp/news/detail/719","website_url":"https://www.oitabus.co.jp","source_date":"2026-10-23","note":"23日12時頃サイト一部再開","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"alsokoki","name":"ALSOK沖縄","service":"会社ホームページ","official_status":"restored","source_url":"https://www.alsok-oki.co.jp/news/corporate/post-946/","website_url":"https://www.alsok-oki.co.jp","source_date":"2026-10-23","note":"23日12時に再開と公表","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"ichibata","name":"一畑電車","service":"会社Webサイト","official_status":"restored","source_url":"https://railway.ichibata.co.jp/news/m_news/%E3%83%9B%E3%83%BC%E3%83%A0%E3%83%9A%E3%83%BC%E3%82%B8%E5%86%8D%E9%96%8B%E3%81%AE%E3%81%8A%E7%9F%A5%E3%82%89%E3%81%9B/","website_url":"https://railway.ichibata.co.jp","source_date":"2026-10-23","note":"再開を公表","subject":"PHP CVE-2026-109618 / CVE-2026-109619","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"junion","name":"j.union","service":"労組向けアプリ等（くみあいアプリは停止継続）","official_status":"partial","source_url":"https://www.j-union.co.jp/news/php%E3%81%AE%E8%84%86%E5%BC%B1%E6%80%A7%E3%81%AB%E5%AF%BE%E3%81%99%E3%82%8B%E4%BA%88%E9%98%B2%E6%8E%AA%E7%BD%AE%E3%81%A8%E3%81%97%E3%81%A6%E3%81%AE%E3%82%B5%E3%83%BC%E3%83%93%E3%82%B9%E4%B8%80/","website_url":"https://www.j-union.co.jp","source_date":"2026-10-23","note":"複数サービス再開、くみあいアプリは継続停止","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"tpec","name":"ティーペック","service":"サービス提供サイト・各オウンドメディア","official_status":"restored","source_url":"https://www.t-pec.co.jp/news/topics/20261023/","website_url":"https://www.t-pec.co.jp","source_date":"2026-10-23","note":"22日19時30分までの停止、再開","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"japio","name":"日本特許情報機構","service":"特許情報検索・AI翻訳・商標スキャナー・公式サイト","official_status":"restored","source_url":"https://japio.or.jp/topics/20261022_01.html","website_url":"https://japio.or.jp","source_date":"2026-10-22","note":"全対象利用可能と公表","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"tokio","name":"東京海上日動","service":"企業サイト・オンライン保険申込・代理店予約等","official_status":"restored","source_url":"https://www.tokiomarine-nichido.co.jp/company/news/261023_01.html","website_url":"https://www.tokiomarine-nichido.co.jp","source_date":"2026-10-23","note":"23日10時までに対象サービス再開","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"fellows","name":"フェローズ","service":"お仕事情報サイト・クリエイターズステーション","official_status":"partial","source_url":"https://www.fellow-s.co.jp/new-s/4677/","website_url":"https://www.fellow-s.co.jp","source_date":"2026-10-22","note":"コーポレートサイト再開、求人関連2サイト停止継続","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"tre","name":"TREホールディングス","service":"コーポレートサイト","official_status":"restored","source_url":"https://www.tre-hd.co.jp/news/627/","website_url":"https://www.tre-hd.co.jp","source_date":"2026-10-23","note":"22日18時30分再開","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"ces","name":"中国電気保安協会","service":"デマンドWeb・太陽光遠隔運転停止システム","official_status":"restored","source_url":"https://www.ces.or.jp/news/important/34.html","website_url":"https://www.ces.or.jp","source_date":"2026-10-23","note":"対象機能を通常再開と公表","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"shadow","name":"UPDATA / Shadow Desktop","service":"Shadow Desktop Manager・製品サイト","official_status":"restored","source_url":"https://www.shadowdesktop.jp/information/20261023/","website_url":"https://www.shadowdesktop.jp","source_date":"2026-10-23","note":"22日22時15分再開","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"aivoice","name":"エーアイ","service":"A.I.VOICE関連サイト・企業サイト等","official_status":"partial","source_url":"https://prtimes.jp/main/html/rd/p/000000192.000099620.html","website_url":"https://www.ai-j.jp","source_date":"2026-10-23","note":"アクティベーションとAICloudは再開、6サイト停止継続","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"neumann","name":"ノイマン","service":"どらスク等の教習所向けサービス","official_status":"partial","source_url":"https://www.neumann.jp/news/4092.html","website_url":"https://www.neumann.jp","source_date":"2026-10-23","note":"どらスク停止中、他サービスは対応中・完了が混在","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"doda-x","name":"doda X（パーソル）","service":"サービス紹介・転職ガイドページ","official_status":"partial","source_url":"https://doda-x.jp/pressroom/info/20261023_01/","website_url":"https://doda-x.jp","source_date":"2026-10-23","note":"マイページ等通常、2ページ停止を公表","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"softbank-emergency","name":"ソフトバンク","service":"緊急速報メール（防災・津波・避難情報）","official_status":"suspended","source_url":"https://www.softbank.jp/corp/news/info/2026/20261023_01/","website_url":"https://www.softbank.jp","source_date":"2026-10-23","note":"23日6時47分から停止、26日完了予定と公表","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"softbank-web","name":"ソフトバンク","service":"ワイモバイル・LINEMO公式トップページ","official_status":"suspended","source_url":"https://www.softbank.jp/corp/news/info/2026/20261022_01/","website_url":"https://www.softbank.jp","source_date":"2026-10-22","note":"公式サイトの緊急メンテナンスを公表、最新完了は要確認","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"rakutenticket","name":"楽天チケット","service":"公式ページ・アプリ","official_status":"suspended","source_url":"https://ticket.rakuten.co.jp/notice/%E3%80%90%E7%B7%8A%E6%80%A5%E3%83%A1%E3%83%B3%E3%83%86%E3%83%8A%E3%83%B3%E3%82%B9%E3%81%AE%E3%81%8A%E7%9F%A5%E3%82%89%E3%81%9B%E3%80%91/","website_url":"https://ticket.rakuten.co.jp","source_date":"2026-10-21","note":"21日22時30分から、再開の確証なし","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"codmon","name":"コドモン","service":"保育施設・保護者アプリ・サイト等","official_status":"restored","source_url":"https://tech.codmon.com/entry/2026/10/23/173909","website_url":"https://www.codmon.com","source_date":"2026-10-23","note":"全対象機能23日9時までに再開した技術記録","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"phiten","name":"ファイテン","service":"ライフテクノロジー・グッドスリープ・健康寿命の家サイト","official_status":"suspended","source_url":"https://www.phiten.com/official-news/20261022-02/","website_url":"https://www.phiten.com","source_date":"2026-10-23","note":"対象3サイト停止、公式通販は利用可能","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"waseda","name":"早稲田大学図書館","service":"古典籍DB・自動書庫・申請フォーム等","official_status":"suspended","source_url":"https://www.waseda.jp/library/news/2026/10/22/30693","website_url":"https://www.waseda.jp","source_date":"2026-10-22","note":"4サービスの停止を公表","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"nagoya","name":"名古屋大学","service":"Nextcloud・VPN・学外アクセス等","official_status":"partial","source_url":"https://icts.nagoya-u.ac.jp/ja/information/maintenance/2026-10-22-phpservice.html","website_url":"https://icts.nagoya-u.ac.jp","source_date":"2026-10-22","note":"学外アクセス制限・停止対象複数、全学システム停止ではない","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"shiga","name":"滋賀県","service":"公開Webシステム143のうち31停止（23日15時）","official_status":"partial","source_url":"https://www.pref.shiga.lg.jp/ce00/press-release/34471.html","website_url":"https://www.pref.shiga.lg.jp","source_date":"2026-10-23","note":"第3報：112公開・31停止","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"base","name":"BASE","service":"ネットショップ・管理画面・PAY ID","official_status":"restored","source_url":"https://help.thebase.in/hc/ja/articles/63455442867737--%E9%87%8D%E8%A6%81-%E7%B7%8A%E6%80%A5%E3%83%A1%E3%83%B3%E3%83%86%E3%83%8A%E3%83%B3%E3%82%B9%E5%AE%8C%E4%BA%86%E3%81%AE%E3%81%8A%E7%9F%A5%E3%82%89%E3%81%9B","website_url":"https://thebase.com","source_date":"2026-10-22","note":"22日8時に完了と公表","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"colorme","name":"カラーミーショップ","service":"ショップ閲覧・管理画面","official_status":"restored","source_url":"https://static-www.shop-pro.jp/news/20261021-maintenance/","website_url":"https://shop-pro.jp","source_date":"2026-10-22","note":"22日8時49分に全メンテナンス完了","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"goope","name":"グーペ","service":"サービス・管理画面・顧客HP","official_status":"restored","source_url":"https://goope.jp/info/maintenance/?date=2026-10","website_url":"https://goope.jp","source_date":"2026-10-22","note":"22日12時30分に完了","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"rakko","name":"ラッコ","service":"ラッコID・キーワード・M&A・ドメインなど6サービス","official_status":"restored","source_url":"https://rakko.inc/news/php2shell-response/","website_url":"https://rakko.inc","source_date":"2026-10-22","note":"22日8時43分全対象再開","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"sega-products","name":"セガ","service":"製品情報サイトおよび一部タイトルサイト","official_status":"partial","source_url":"https://www.sega.jp/important_infos/detail/261023_3/","website_url":"https://www.sega.jp","source_date":"2026-10-23","note":"製品サイト23日11時30分再開、個別タイトルサイトは一部停止継続","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"sega-id","name":"セガ","service":"SEGA IDログイン・登録・決済関連","official_status":"restored","source_url":"https://gw.sega.jp/gateway/news/index.html?category=2&id=612","website_url":"https://gw.sega.jp","source_date":"2026-10-22","note":"22日14時メンテ終了、各個別サービスの状態は別","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"mpi","name":"mpi松香フォニックス","service":"りすおん・発音チェッカー・TAGAKI特別サイト","official_status":"restored","source_url":"https://www.mpi-j.co.jp/news/2190/","website_url":"https://www.mpi-j.co.jp","source_date":"2026-10-23","note":"23日から順次再開","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"icnet","name":"アイ・シー・ネット","service":"コーポレートサイト","official_status":"restored","source_url":"https://www.icnet.co.jp/news/7703/","website_url":"https://www.icnet.co.jp","source_date":"2026-10-23","note":"22日18時停止後、23日再開","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"thann","name":"THANN","service":"公式オンラインショップ","official_status":"restored","source_url":"https://www.thann-natural.co.jp/f/news2026.10.23","website_url":"https://www.thann-natural.co.jp","source_date":"2026-10-23","note":"22日23時35分復旧","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"jtax","name":"日本税理士会連合会","service":"公式ホームページ","official_status":"restored","source_url":"https://www.nichizeiren.or.jp/whats-new/20261023a/","website_url":"https://www.nichizeiren.or.jp","source_date":"2026-10-23","note":"23日14時30分再開","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"cst","name":"コンピュータシステム研究所","service":"ALTA Revolution等、ROOK一部","official_status":"partial","source_url":"https://www.cstnet.co.jp/topics/261022m.html","website_url":"https://www.cstnet.co.jp","source_date":"2026-10-22","note":"ALTA関連と一部ROOK機能継続停止","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"rakutenpasha","name":"楽天Pasha","service":"クーポン・レシート申請等","official_status":"restored","source_url":"https://pasha.rakuten.co.jp/special/spot/notification_202610_maintenance/","website_url":"https://pasha.rakuten.co.jp","source_date":"2026-10-22","note":"21日22時30分〜22日6時30分終了","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"milabo","name":"ミラボ","service":"子育てモバイル","official_status":"restored","source_url":"https://mi-labo.co.jp/posts/20261021-php-security/","website_url":"https://mi-labo.co.jp","source_date":"2026-10-23","note":"21日23時13分から22日23時40分まで停止","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"},{"id":"shinkyo","name":"長崎市北部商工会","service":"トリコPAY","official_status":"restored","source_url":"https://r.goope.jp/srp-42/shokokai/info","website_url":"https://r.goope.jp","source_date":"2026-10-22","note":"22日16時08分に再開","subject":"PHP-related precautionary service suspension / remediation","region":"JP","evidence_tier":"first_party","verification_date":"2026-10-24"}];
const PHP_PROVIDER_SOURCES = Object.freeze([
  {id:"kinsta",name:"Kinsta",url:"https://status.kinsta.com"},
  {id:"pantheon",name:"Pantheon",url:"https://status.pantheon.io"},
  {id:"acquia",name:"Acquia",url:"https://status.acquia.com"},
  {id:"cloudways",name:"Cloudways",url:"https://status.cloudways.com"}
]);
const PHP_LAST="php:latest:v1";
const PHP_HISTORY="php:history:v1";
const PHP_HEALTH="php:health:v1";
async function phpLimitedMap(items,limit,callback) {
  const out=Array(items.length);
  let pointer=0;
  await Promise.all(Array.from({length:Math.min(limit,items.length)},async()=>{
    while(pointer<items.length){const i=pointer++;out[i]=await callback(items[i],i);}
  }));
  return out;
}
async function phpWebsiteCheck(record,previous) {
  const checkedAt=new Date().toISOString();
  const prev=previous||{};
  try {
    // Fixed allowlisted public HTTPS homepage URLs only, no dynamic URLs, no query/body.
    if(!/^https:\/\/[a-z0-9.-]+\/?$/i.test(record.website_url))
      return {reachability:"not_applicable",checked_at:checkedAt,http_status:null,consecutive_failures:0};
    const response=await fetch(record.website_url,{
      method:"HEAD",redirect:"manual",signal:AbortSignal.timeout(8500),
      headers:{"User-Agent":"ResoArc-Service-Outage-Observatory/1.0 (+https://resoarc.com/status/)"}
    });
    const code=response.status;
    const timeoutOr5xx=code>=500 || code===0;
    const strikes=timeoutOr5xx?(prev.consecutive_failures||0)+1:0;
    return {reachability:timeoutOr5xx?(strikes>=2?"suspected_unavailable":"possible_issue"):
          code>=400?"unverified_access": "http_responding",
      checked_at:checkedAt,http_status:code,consecutive_failures:strikes};
  }catch{
    const strikes=(prev.consecutive_failures||0)+1;
    return {reachability:strikes>=2?"suspected_unavailable":"possible_issue",
      checked_at:checkedAt,http_status:null,consecutive_failures:strikes};
  }
}
async function phpProviderCheck(source) {
  const checkedAt=new Date().toISOString();
  try {
    const response=await fetch(source.url+"/api/v2/summary.json",{
      headers:{"Accept":"application/json"},signal:AbortSignal.timeout(8500)});
    if(!response.ok)throw new Error("status_"+response.status);
    const data=await response.json();
    if(!data.status || !Array.isArray(data.incidents))throw new Error("unknown_format");
    return {id:source.id,name:source.name,source_url:source.url,checked_at:checkedAt,
      source_access:"ok",overall_status:String(data.status.indicator||"unknown").slice(0,24),
      incidents:data.incidents.slice(0,12).map(x=>({
        id:String(x.id||"").slice(0,90),name:String(x.name||"").slice(0,220),
        status:String(x.status||"unknown").slice(0,35),
        impact:String(x.impact||"unknown").slice(0,35),
        updated_at:x.updated_at||null,
        is_php_related:/php|wordpress|drupal|site|server|hosting/i.test(x.name||"")
      }))};
  }catch{return {id:source.id,name:source.name,source_url:source.url,
    checked_at:checkedAt,source_access:"unavailable",overall_status:"unknown",incidents:[]};}
}
async function collectPhp(env,kind) {
  const now=new Date().toISOString();
  const prev=await env.OUTAGES.get(PHP_LAST,"json");
  const previousById=new Map((prev?.companies||[]).map(x=>[x.id,x.website_check]));
  // Keep external request count bounded as the corpus grows: 24 HEAD checks per hour.
  // All other sites retain the last observation with its original checked_at timestamp.
  const rotation=Math.floor(Date.now()/3600000)*24;
  const sampled=new Set(Array.from({length:Math.min(24,PHP_REGISTRY.length)},
    (_,i)=>PHP_REGISTRY[(rotation+i)%PHP_REGISTRY.length].id));
  const [companies,providers,discovery,review]=await Promise.all([
    phpLimitedMap(PHP_REGISTRY,5,async record=>({
      ...record,website_check:sampled.has(record.id)
        ?await phpWebsiteCheck(record,previousById.get(record.id))
        :(previousById.get(record.id)||{
          reachability:"not_applicable",checked_at:null,http_status:null,consecutive_failures:0})
    })),
    phpLimitedMap(PHP_PROVIDER_SOURCES,4,phpProviderCheck),
    phpDiscover(env),
    phpRecheckOfficial(env)
  ]);
  for(const company of companies){
    const latest=review.overrides[company.id];
    if(latest){
      company.official_review={checked_at:latest.checked_at,source_url:latest.source_url||company.source_url,
        review_note:latest.review_note,updated_status:latest.updated_status||null};
      if(latest.updated_status && latest.updated_status!==company.official_status){
        company.declared_status=company.official_status;
        company.official_status=latest.updated_status;
        company.auto_status_updated=true;
      }
    }
  }

  const stats={
    newly_discovered_candidates:discovery.items.length,
    publisher_feed_errors:discovery.failed_queries,
    official_pages_rechecked:review.checked,
    official_recheck_errors:review.failed,
    published_suspended:companies.filter(x=>x.official_status==="suspended").length,
    published_partial:companies.filter(x=>x.official_status==="partial").length,
    published_restored:companies.filter(x=>x.official_status==="restored").length,
    suspected_unavailable:companies.filter(x=>x.website_check.reachability==="suspected_unavailable").length,
    probe_unverified:companies.filter(x=>["unverified_access","possible_issue","not_applicable"].includes(x.website_check.reachability)).length,
    provider_sources_unavailable:providers.filter(x=>x.source_access!=="ok").length
  };
  const snapshot={
    schema_version:"1.0",type:"corporate_php_outages",collection_mode:"hourly_cron",
    collected_at:now,last_success_at:now,source_as_of:"2026-10-24T01:23:00+09:00",
    cases_total:companies.length,provider_total:providers.length,
    stats,companies,providers,
    discovery:{checked_at:discovery.checked_at,quality:discovery.quality,
      publisher_feed_errors:discovery.failed_queries,fallback_sources_used:discovery.fallback_sources_used,
      diagnostics:discovery.errors,items:discovery.items},
    note:"各社公式告知に基づく公表状況。公表日以降の復旧は自動確定しません。HTTPは外形応答のみで個別の停止サービスの稼働保証ではありません。",
    source_update_policy:"New reports are automatically discovered from public news RSS into an unverified candidates panel. Registered official announcements are rechecked in rotating batches, and only explicit full-recovery or partial-recovery expressions can update the displayed notice status. Unconfirmed reports never become confirmed automatically.",
    probe_policy:"Rotating up to 24 fixed public homepages each hour by HEAD. Two consecutive failures lead to suspected unavailability; 401/403 remain unverified. Last-checked times are preserved.",
    history_retention_days:30
  };
  let history=await env.OUTAGES.get(PHP_HISTORY,"json");
  if(!Array.isArray(history))history=[];
  history.push({collected_at:now,stats});
  history=history.filter(x=>Date.parse(x.collected_at)>Date.now()-RETENTION*1000).slice(-720);
  await env.OUTAGES.put(PHP_LAST,JSON.stringify(snapshot));
  await env.OUTAGES.put(PHP_HISTORY,JSON.stringify(history));
  await env.OUTAGES.put(PHP_HEALTH,JSON.stringify({last_success_at:now,
     last_attempt_at:now,status:"success",trigger:kind}));
  console.log("PHP_HOURLY_PASS",companies.length,providers.length,JSON.stringify(stats));
  return snapshot;
}
async function readPhp(env) {
  const latest=await env.OUTAGES.get(PHP_LAST,"json");
  if(!latest)return {error:"php_feed_not_initialized",quality:"UNAVAILABLE"};
  const health=await env.OUTAGES.get(PHP_HEALTH,"json");
  const discovery=await env.OUTAGES.get(PHP_DISCOVERY_KEY,"json");
  const latestDiscovery=discovery?.checked_at&&
     Date.parse(discovery.checked_at)>Date.parse(latest.discovery?.checked_at||"1970-01-01")
      ?discovery:latest.discovery;
  return {...latest,discovery:latestDiscovery,
    stats:{...latest.stats,newly_discovered_candidates:latestDiscovery?.items?.length||0,
      publisher_feed_errors:latestDiscovery?.failed_queries||0},
    stale:expired(latest.collected_at),last_attempt_status:health?.status||"unknown"};
}


/* PHP notice discovery and official-source recheck: data-only, scoped, bounded. */
const PHP_DISCOVERY_KEY="php:discovery:v1";
const PHP_OVERRIDE_KEY="php:official_updates:v1";
const PHP_DISCOVERY_QUERIES=[
  "PHP 脆弱性 一時停止 再開 when:5d",
  "PHP2Shell サービス 停止 復旧 2026 when:5d",
  "PHP 脆弱性 会社 一部停止 メンテナンス when:5d"
];
const phpXmlUnescape=(s)=>String(s||"").replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g,"$1")
.replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">")
.replace(/&quot;/g,'"').replace(/&#39;|&apos;/g,"'")
.replace(/&#(x[0-9a-f]+|\d+);/gi,(_,v)=>{
 const code=v[0].toLowerCase()==="x"?parseInt(v.slice(1),16):Number(v);
 return code>0&&code<=0x10ffff?String.fromCodePoint(code):"";
}).trim();
const phpSafePublicHost=(value)=>{
  try {
    const x=new URL(value);
    if(x.protocol!=="https:"||x.username||x.password||x.port||x.hash) return false;
    const h=x.hostname.toLowerCase();
    if(h==="localhost" || h.endsWith(".local")||h.endsWith(".internal")||
      /^(?:127|0|10|192\.168)\./.test(h)||/^172\.(?:1[6-9]|2\d|3[01])\./.test(h))return false;
    return true;
  }catch{return false;}
};
function phpRssParse(xml) {
  const found=[];
  for(const item of xml.match(/<item(?:\s[^>]*)?>[\s\S]*?<\/item>/g)||[]){
    const field=(tag)=>phpXmlUnescape((item.split("<"+tag+">")[1]||"").split("</"+tag+">")[0]);
    const sourceMatch=item.match(/<source\s+url="([^"]+)"[^>]*>([\s\S]*?)<\/source>/i);
    const title=field("title").slice(0,240);
    const url=field("link").slice(0,400);
    let source_url=phpXmlUnescape(sourceMatch?.[1]||"");
    let publisher=phpXmlUnescape(sourceMatch?.[2]||"").slice(0,100);
    let link=url;
    if(/^https?:\/\/(?:www\.)?bing\.com\/news\/apiclick\.aspx/.test(url)){
      try{link=new URL(url).searchParams.get("url")||url;}catch{link=url;}
    }
    if(!source_url && phpSafePublicHost(link)){
      try{source_url=new URL(link).origin;}catch{source_url="";}
    }
    if(!publisher)publisher=title.includes(" - ")?title.split(" - ").slice(-1)[0].slice(0,100):"ニュース検索（配信元未確認）";
    const published=new Date(field("pubDate"));
    if(!title||!phpSafePublicHost(source_url)||Number.isNaN(published.getTime()) ||
       published.getTime()<Date.now()-7*86400000 ||
       !/PHP|php2shell|脆弱性/.test(title)||
       !/停止|休止|メンテナンス|再開|復旧|影響|対策|修正/.test(title)) continue;
    found.push({id: encodeURIComponent(link).slice(0,100),
      title,link:phpSafePublicHost(link)?link:url,publisher,publisher_url:source_url,
      published_at:published.toISOString(),status:"discovery_unverified",
      note:"ニュースRSSで発見。公式発表の本文と対象サービスの確認が未完了です。稼働状況への自動判定はしません。"});
  }
  return found;
}
async function phpDiscover(env){
  const previous=await env.OUTAGES.get(PHP_DISCOVERY_KEY,"json");
  const existing=Array.isArray(previous?.items)?previous.items:[];
  if(previous?.source==="vps_cron" && Date.now()-Date.parse(previous.checked_at)<100*60000)
    return previous;
  const responses=await phpLimitedMap(PHP_DISCOVERY_QUERIES,2,async q=>{
    try{
      const source="https://news.google.com/rss/search?q="+encodeURIComponent(q)+"&hl=ja&gl=JP&ceid=JP:ja";
      const r=await fetch(source,{headers:{"Accept":"application/rss+xml"},signal:AbortSignal.timeout(10000)});
      if(!r.ok)throw Error("http_"+r.status);
      const raw=(await r.text()).slice(0,600000);
      if(!raw.startsWith("<?xml")&&!raw.includes("<rss"))throw Error("not_rss");
      return {status:"OK",items:phpRssParse(raw)};
    }catch(e){
      // Google News blocks some datacenter egress. Use Bing's public RSS as a bounded fallback.
      const primary=String(e.message||e).slice(0,60);
      try {
        const fallback="https://www.bing.com/news/search?q="+encodeURIComponent(q)+"&format=rss&mkt=ja-jp";
        const secondary=await fetch(fallback,{headers:{"Accept":"application/rss+xml"},
          signal:AbortSignal.timeout(8500)});
        if(!secondary.ok)throw Error("bing_http_"+secondary.status);
        const rss=(await secondary.text()).slice(0,350000);
        if(!rss.includes("<rss"))throw Error("bing_not_rss");
        return {status:"OK_FALLBACK",items:phpRssParse(rss)};
      }catch(err){
        return {status:"FAILED",items:[],reason:primary+";fallback:"+String(err.message||err).slice(0,60)};
      }
    }
  });
  const map=new Map();
  for(const a of [...responses.flatMap(x=>x.items),...existing]){
    if(!map.has(a.link))map.set(a.link,a);
  }
  const rows=[...map.values()].sort((a,b)=>b.published_at.localeCompare(a.published_at))
    .filter(x=>Date.parse(x.published_at)>Date.now()-7*86400000).slice(0,120);
  const result={checked_at:new Date().toISOString(),quality:responses.every(x=>x.status!=="FAILED")?"OK":"PARTIAL",
    queries_checked:responses.length,failed_queries:responses.filter(x=>x.status==="FAILED").length,
    fallback_sources_used:responses.filter(x=>x.status==="OK_FALLBACK").length,
    errors:responses.filter(x=>x.status==="FAILED").map(x=>x.reason).slice(0,3),
    items:rows};
  await env.OUTAGES.put(PHP_DISCOVERY_KEY,JSON.stringify(result));
  return result;
}
function phpBodyText(html){
  return String(html||"").slice(0,400000)
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi," ")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi," ")
    .replace(/<[^>]+>/g," ").replace(/&nbsp;|&#160;/g," ")
    .replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">")
    .replace(/\s+/g," ").slice(0,70000);
}
function phpOfficialState(text){
  // Evidence must be explicit, first-party and apply to all targeted services.
  if(!/PHP|脆弱性|緊急メンテナンス/.test(text))return null;
  const mixed=/引き続き.{0,35}(?:停止|休止|メンテナンス)|(?:停止|休止).{0,12}継続|一部.{0,24}(?:停止|未再開)|個別.{0,16}(?:引き続き|メンテナンス)/.test(text);
  const all=/すべての(?:対象)?サービス.{0,50}(?:再開|復旧)|全(?:対象|てのサービス|サービス).{0,35}(?:復旧|再開)|すべての.{0,30}メンテナンス.{0,10}完了|現在は.{0,12}通常どおり.{0,12}(?:ご利用|稼働)|再開いたしました.{0,15}(?:今後|引き続き)/.test(text);
  const some=/一部.{0,22}再開|順次再開|再開したサービス|対応を完了したものから/.test(text);
  if(mixed&&some)return "partial";
  if(!mixed&&all)return "restored";
  return null;
}
async function phpRecheckOfficial(env,prior) {
  const saved=await env.OUTAGES.get(PHP_OVERRIDE_KEY,"json");
  const overrides=saved&&typeof saved==="object"?saved:{};
  const now=new Date().toISOString();
  const hour=Math.floor(Date.now()/3600000);
  const n=PHP_REGISTRY.length;
  // Rotate 8 first-party notices each hour, no arbitrary HTTP or RSS URL follow.
  const selected=Array.from({length:Math.min(8,n)},(_,i)=>PHP_REGISTRY[(hour*8+i)%n])
    .filter(x=>x.evidence_tier!=="unverified_primary"&&phpSafePublicHost(x.source_url));
  const observations=await phpLimitedMap(selected,4,async record=>{
    try {
      const resp=await fetch(record.source_url,{redirect:"manual",
        headers:{"Accept":"text/html"},signal:AbortSignal.timeout(9000)});
      if(!resp.ok||!(resp.headers.get("content-type")||"").includes("text/html"))
        throw Error("official_not_html");
      const text=phpBodyText(await resp.text());
      const proposed=phpOfficialState(text);
      const update={checked_at:now,http_status:resp.status,
        status_inferred:proposed,source_url:record.source_url,
        review_note:proposed?"公式本文の明確な状態表現を検出。":"公式本文を確認、明確な全体再開は判定できませんでした。"};
      // Do not automatically misclassify a previously restored system as down from an old notice.
      if(proposed==="restored" && record.official_status!=="restored")
        update.updated_status="restored";
      else if(proposed==="partial"&&record.official_status==="suspended")
        update.updated_status="partial";
      overrides[record.id]=update;
      return {id:record.id,success:true,proposed};
    }catch{
      overrides[record.id]={...(overrides[record.id]||{}),checked_at:now,http_status:null,
        review_note:"公式ソースへの再接続ができませんでした。前回の確認状態を保留します。"};
      return {id:record.id,success:false};
    }
  });
  await env.OUTAGES.put(PHP_OVERRIDE_KEY,JSON.stringify(overrides));
  return {overrides,checked:observations.length,failed:observations.filter(x=>!x.success).length};
}


async function phpRssDiagnostics(request) {
  if(request.method!=="GET")return json({error:"method_not_allowed"},405);
  if(new URL(request.url).search)return json({error:"invalid_query"},400);
  const test=async(name,url)=>{
    try{
      const res=await fetch(url,{headers:{"Accept":"application/rss+xml"},
        signal:AbortSignal.timeout(8500)});
      const body=(await res.text()).slice(0,350000);
      return {name,http_status:res.status,looks_like_rss:body.includes("<rss"),
        bytes:body.length,candidates:phpRssParse(body).length};
    }catch(e){return {name,error:String(e.message||e).slice(0,100)};}
  };
  const q="PHP 脆弱性 一時停止 when:4d";
  return json({checked_at:new Date().toISOString(),results:await Promise.all([
    test("Google News","https://news.google.com/rss/search?q="+encodeURIComponent(q)+"&hl=ja&gl=JP&ceid=JP:ja"),
    test("Bing News","https://www.bing.com/news/search?q="+encodeURIComponent(q)+"&format=rss&mkt=ja-jp")
  ])});
}

/* One bounded, rate-limited recheck of provider-owned RSS sources. */
async function phpRefreshDiscovery(request,env) {
  if(request.method!=="GET")return json({error:"method_not_allowed"},405);
  if(new URL(request.url).search)return json({error:"unsupported_query"},400);
  const previous=await env.OUTAGES.get(PHP_DISCOVERY_KEY,"json");
  const age=Date.now()-Date.parse(previous?.checked_at||"1970-01-01");
  if(age<60*60000)
    return json({refreshed:false,reason:"already_fresh",checked_at:previous.checked_at,
      candidates:previous.items?.length||0});
    const data=await phpDiscover(env);
  return json({refreshed:true,checked_at:data.checked_at,quality:data.quality,
    candidates:data.items?.length||0,failed_queries:data.failed_queries,
    fallback_sources_used:data.fallback_sources_used||0});
}
