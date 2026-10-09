/* "Further explanation": an animated walkthrough of what the quantum layer (Q-Gate) did with THIS
   message, built from the real trace (sentence scores, qubit angles, nearest known attacks, verdict).
   Ends with the full raw trace for engineers. Pure DOM + CSS animations. */
"use strict";
(function () {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const REVIEW = 0.5, QUAR = 0.8;

  const byte = (cls = "") => `<svg class="byte ${cls}" viewBox="0 0 64 40" aria-hidden="true">
    <path d="M6 30 C2 22 4 16 10 14" class="wagx"/><ellipse cx="22" cy="28" rx="16" ry="7" class="f"/>
    <ellipse cx="18" cy="26" rx="4" ry="2.4" class="k"/><path d="M12 34 v5 M30 34 v5"/>
    <circle cx="42" cy="20" r="9" class="f"/><ellipse cx="52" cy="23" rx="7" ry="4.5" class="f"/>
    <circle cx="58" cy="22" r="2.4" class="k"/><circle cx="43" cy="17" r="1.6" class="k"/>
    <path d="M36 14 C30 15 31 26 35 29 C38 24 39 17 36 14 Z" class="w"/></svg>`;

  const sleepy = `<svg class="byte big" viewBox="0 0 120 70" aria-hidden="true">
    <ellipse cx="54" cy="52" rx="34" ry="12" class="f"/><ellipse cx="44" cy="48" rx="6" ry="3" class="k"/>
    <circle cx="88" cy="46" r="13" class="f"/><path d="M82 44 q4 3 8 0" /><path d="M78 38 C70 40 72 54 78 56 C82 50 82 42 78 38 Z" class="w"/>
    <ellipse cx="100" cy="50" rx="8" ry="5" class="f"/><circle cx="106" cy="49" r="2.4" class="k"/>
    <path d="M20 54 C10 52 10 44 16 42"/><text x="96" y="22" class="zz z1">z</text><text x="104" y="12" class="zz z2">Z</text></svg>`;

  function dials(feats, big = true) {
    const R = big ? 26 : 9, gap = big ? 100 : 26, w = gap * 3 + R * 2 + 12, h = big ? 92 : 26, cy = big ? 40 : 13;
    let out = `<svg class="dials ${big ? "" : "mini"}" viewBox="0 0 ${w} ${h}" aria-hidden="true">`;
    feats.forEach((f, i) => {
      const cx = R + 6 + i * gap, deg = (f * 180) / Math.PI;
      if (i < 3) out += `<path d="M${cx + R} ${cy} C${cx + R + 14} ${cy - 14} ${cx + gap - R - 14} ${cy + 14} ${cx + gap - R} ${cy}" class="link" style="--t:${big ? 1.1 + i * 0.25 : 0}s"/>`;
      out += `<circle cx="${cx}" cy="${cy}" r="${R}" class="f"/>
        <g class="needle" style="--rot:${deg.toFixed(1)}deg; --t:${big ? 0.3 + i * 0.25 : 0}s; transform-origin:${cx}px ${cy}px">
          <path d="M${cx} ${cy} L${cx} ${cy - R + 4}" class="wine"/><circle cx="${cx}" cy="${cy - R + 4}" r="${big ? 3.2 : 1.6}" class="wfill"/></g>
        <circle cx="${cx}" cy="${cy}" r="${big ? 2.5 : 1.2}" class="k"/>`;
      if (big) out += `<text x="${cx}" y="${cy + R + 18}" class="lab">q${i} = ${f.toFixed(2)}</text>`;
    });
    return out + "</svg>";
  }

  function quantumStory(it, config) {
    const steps = it.trace?.steps || [], flags = it.trace?.flags || {};
    const qs = steps.filter((s) => s.stage === "content" && s.qgate);
    if (!flags.QGATE && !flags.CLASSICAL) return `<div class="qx-idle">${sleepy}<div><b>Byte was off duty.</b> The quantum layer is switched off in
      this configuration (<code>${esc(config)}</code>). Pick <b>Aegis · Full protection</b> in the dropdown to watch it work.</div></div>`;
    if (!qs.length) return `<div class="qx-idle">${sleepy}<div><b>Nothing to sniff.</b> Q-Gate only checks what the AI <i>reads</i>
      (documents, files, tool results), not what you type. This turn read nothing, so Byte had a nap.</div></div>`;

    const top = qs.reduce((a, b) => (b.qgate.score > a.qgate.score ? b : a));
    const d = top.qgate.details || {}, sents = d.sentences || [], score = +top.qgate.score, dec = top.qgate.decision;
    const ti = d.top ?? sents.findIndex((x) => x.score === score);
    const n = sents.length, t1 = 0.6 + n * 0.45;                 // when the sentence sweep finishes
    const verdict = dec === "quarantine" ? "QUARANTINED" : dec === "review" ? "FLAGGED FOR REVIEW" : "ALL CLEAR";
    const verdictLine = dec === "quarantine" ? "The sentence was removed before the AI ever read it."
      : dec === "review" ? "The text stays, but anything risky the AI tries next needs your approval."
      : "Nothing here looked like an injected command, so the text went through untouched.";
    const near = d.nearest_attacks || [], benign = (d.nearest_benign || [])[0];

    return `<div class="qx">
      <section class="beat" style="--t:.1s"><h4><span class="num">1</span> Byte sniffs every sentence of <code>${esc(top.origin)}</code></h4>
        <div class="sn">${sents.map((x, i) => `<div class="sn-row ${i === ti ? "top" : ""}" style="--t:${(0.6 + i * 0.45).toFixed(2)}s; --w:${Math.max(2, x.score * 100).toFixed(0)}%">
          <span class="sn-dog">${byte()}</span><span class="sn-text">${esc(x.text)}</span>
          <span class="sn-bar"><i></i><b class="mark r"></b><b class="mark q"></b></span><span class="sn-score">${x.score.toFixed(2)}</span></div>`).join("")}</div>
        <p class="note">One bad sentence is enough, so the <b>highest</b> score counts. Lines: <span class="amber">review 0.50</span> · <span class="wine">quarantine 0.80</span>.</p></section>

      <section class="beat" style="--t:${t1.toFixed(2)}s"><h4><span class="num">2</span> The sneakiest sentence is squeezed into 4 numbers</h4>
        <div class="squeeze"><blockquote>“${esc(sents[ti]?.text || "")}”</blockquote><span class="arrow">→</span>
          <div class="chips">${(d.features || []).map((f, i) => `<span class="chip4" style="--t:${(t1 + 0.4 + i * 0.2).toFixed(2)}s">${f.toFixed(2)}</span>`).join("")}</div></div>
        <p class="note">Character patterns (TF-IDF) are compressed to the 4 strongest directions (SVD), scaled to 0…π, one per qubit.</p></section>

      <section class="beat" style="--t:${(t1 + 1.4).toFixed(2)}s"><h4><span class="num">3</span> Each number twists one qubit, and neighbours get tangled</h4>
        <div class="dial-wrap" style="--t0:${(t1 + 1.4).toFixed(2)}s">${dials(d.features || [0, 0, 0, 0])}</div>
        <p class="note">RZ rotations by each feature, then entangling links between neighbours (the ZZ feature map), so the state also encodes <i>pairs</i> of features. Simulated exactly on this laptop.</p></section>

      <section class="beat" style="--t:${(t1 + 3).toFixed(2)}s"><h4><span class="num">4</span> Its quantum state is compared with known attacks</h4>
        <div class="near">${near.map((x, i) => `<div class="near-row" style="--t:${(t1 + 3.3 + i * 0.3).toFixed(2)}s; --w:${(x.k * 100).toFixed(0)}%">
            ${dials(d.features || [0, 0, 0, 0], false)}<span class="vs">≈</span><span class="near-text">“${esc(x.text)}”</span>
            <span class="near-bar"><i></i></span><span class="near-k">${x.k.toFixed(2)}</span></div>`).join("")}
          ${benign ? `<div class="near-row benign" style="--t:${(t1 + 3.3 + near.length * 0.3).toFixed(2)}s; --w:${(benign.k * 100).toFixed(0)}%">
            ${dials(d.features || [0, 0, 0, 0], false)}<span class="vs">≈</span><span class="near-text">closest normal text: “${esc(benign.text)}”</span>
            <span class="near-bar"><i></i></span><span class="near-k">${benign.k.toFixed(2)}</span></div>` : ""}</div>
        <p class="note">Similarity = how much two quantum states overlap, |⟨φ(a)|φ(b)⟩|² (1 = identical). The SVM weighs the overlaps with
          <i>all</i> ${near.length ? "training examples" : "examples"}, not just these, to place the sentence on the attack or normal side.</p></section>

      <section class="beat" style="--t:${(t1 + 4.6).toFixed(2)}s"><h4><span class="num">5</span> The verdict</h4>
        <div class="meter"><div class="zone z1"></div><div class="zone z2"></div><div class="zone z3"></div>
          <div class="needle-m" style="--x:${(score * 100).toFixed(1)}%; --t:${(t1 + 4.9).toFixed(2)}s"><span>${score.toFixed(2)}</span></div>
          <div class="mticks"><span style="left:50%">0.5 review</span><span style="left:80%">0.8 quarantine</span></div></div>
        <div class="stamp-row"><div class="stamp2 ${dec}" style="--t:${(t1 + 6).toFixed(2)}s">${verdict}</div>
          <div class="stamp-note">${verdictLine}${top.twin ? `<br><span class="mut">Classical twin (RBF, same 4 features) scored ${(+top.twin.score).toFixed(2)} → ${esc(top.twin.decision)}. Shown for comparison; it does not decide.</span>` : ""}
          <br><span class="mut">Q-Gate only advises: even if it misses, plain-code rules still block the dangerous action.</span></div></div></section>
    </div>`;
  }

  window.openExplain = function (it, rawHtml, config) {
    const body = document.querySelector("#drawerBody");
    document.querySelector("#drawerTitle").textContent = "Further explanation";
    const render = () => {
      body.innerHTML = `<div class="ex-head"><div><div class="ex-title">How the quantum layer saw this</div>
        <div class="ex-sub">replayed from this exact message · real scores, real qubit angles</div></div>
        <button class="btn" id="exReplay">↻ replay</button></div>${quantumStory(it, config)}
        <details class="rawd"><summary>Every check, step by step (raw trace for engineers)</summary>${rawHtml}</details>`;
      document.querySelector("#exReplay").onclick = render;
    };
    render();
    document.querySelector("#drawer").hidden = false;
  };
})();
