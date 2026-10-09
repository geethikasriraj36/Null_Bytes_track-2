/* "Further explanation": an animated walkthrough of what the quantum layer (Q-Gate) did with THIS message,
   built from the real trace: sentence scores, the 4 features, Bloch-sphere rotations, the 16 amplitude phases
   of the actual 4-qubit state (computed here with the same ZZ feature map Q-Gate uses), the nearest known
   attacks and the verdict. Ends with the raw trace for engineers. Pure DOM + SVG + CSS/JS animation. */
"use strict";
(function () {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const PI = Math.PI;

  /* ------------------------------------------------------------ physics (matches aegis/qgate/kernel.py)
     |phi(x)> = U_ZZ(x) H^4 |0000>: Hadamards, RZ(x_i) on qubit i, then CNOT-RZ((pi-x_i)(pi-x_j))-CNOT on
     neighbours. Everything after the Hadamards is diagonal, so every basis state |b> keeps amplitude 1/4 and
     only gains a phase:  theta(b) = sum_i s(b_i) x_i/2 + sum_i s(b_i XOR b_i+1) (pi-x_i)(pi-x_i+1)/2,
     with s(0) = -1, s(1) = +1 (RZ(a) = diag(e^-ia/2, e^+ia/2)). Qubit 0 is the leftmost bit. */
  function phases(x) {
    const out = [];
    for (let b = 0; b < 16; b++) {
      const bit = (i) => (b >> (3 - i)) & 1, s = (v) => (v ? 1 : -1);
      let th = 0;
      for (let i = 0; i < 4; i++) th += s(bit(i)) * x[i] / 2;
      for (let i = 0; i < 3; i++) th += s(bit(i) ^ bit(i + 1)) * (PI - x[i]) * (PI - x[i + 1]) / 2;
      out.push({ label: b.toString(2).padStart(4, "0"), theta: Math.atan2(Math.sin(th), Math.cos(th)) });
    }
    return out;
  }

  /* ------------------------------------------------------------ little drawings */
  const atom = () => `<svg class="atom" viewBox="0 0 30 30" aria-hidden="true"><g class="orbits">
      <ellipse cx="15" cy="15" rx="13" ry="5"/><ellipse cx="15" cy="15" rx="13" ry="5" transform="rotate(60 15 15)"/>
      <ellipse cx="15" cy="15" rx="13" ry="5" transform="rotate(-60 15 15)"/></g><circle cx="15" cy="15" r="2.6" class="nuc"/></svg>`;

  // a Bloch sphere; the state arrow starts on the equator (after H) and swings by `angle` around the z axis
  function bloch(i, angle, opts = {}) {
    const R = opts.R || 34, cx = R + 10, cy = R + 22, ry = R * 0.32, w = 2 * R + 20, h = 2 * R + (opts.label ? 52 : 34);
    return `<svg class="bloch" viewBox="0 0 ${w} ${h}" data-angle="${angle}" data-r="${R}" data-cx="${cx}" data-cy="${cy}" data-ry="${ry}"
        data-rest="${opts.rest ? 1 : 0}" aria-hidden="true">
      <circle cx="${cx}" cy="${cy}" r="${R}" class="sphere"/>
      <ellipse cx="${cx}" cy="${cy}" rx="${R}" ry="${ry}" class="equator back"/>
      <path d="M${cx - R} ${cy} A${R} ${ry} 0 0 0 ${cx + R} ${cy}" class="equator front"/>
      <path d="M${cx} ${cy - R - 4} L${cx} ${cy + R + 4}" class="axis"/>
      <text x="${cx}" y="${cy - R - 8}" class="ket">|0⟩</text><text x="${cx}" y="${cy + R + 16}" class="ket">|1⟩</text>
      <line x1="${cx}" y1="${cy}" x2="${opts.rest ? cx : cx + R}" y2="${opts.rest ? cy - R : cy}" class="vec"/>
      <circle cx="${opts.rest ? cx : cx + R}" cy="${opts.rest ? cy - R : cy}" r="4" class="tip"/>
      <circle cx="${cx}" cy="${cy}" r="2.4" class="nucleus"/>
      ${opts.label ? `<text x="${cx}" y="${h - 4}" class="lab">${opts.label}</text>` : ""}</svg>`;
  }

  function clocks(ph) {
    return `<div class="phase-grid">${ph.map((p, i) => `<div class="phase" style="--t2:${(i * 0.06).toFixed(2)}s; --rot:${(p.theta * 180 / PI).toFixed(1)}deg">
      <svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="15" class="dial"/><circle cx="20" cy="20" r="15" class="glow"/>
        <g class="hand"><line x1="20" y1="20" x2="33" y2="20"/><circle cx="33" cy="20" r="2.4"/></g><circle cx="20" cy="20" r="1.8" class="hub"/></svg>
      <span>|${p.label}⟩</span></div>`).join("")}</div>`;
  }


  /* ------------------------------------------------------------ the cast: Alice (asks), Bob (Aegis), Eve (the attacker in the doc)
     Original 90s-comic style faces: big round heads, dot eyes, simple ink lines. */
  const CAST = { alice: "Alice", bob: "Bob", eve: "Eve" };
  function face(who) {
    const eyes = who === "eve" ? `<path d="M19 30 q3 -2 6 0 M31 30 q3 -2 6 0" class="ink-l"/><path d="M18 25 l7 2 M38 25 l-7 2" class="ink-l"/>`
      : `<circle cx="22" cy="30" r="2.2" class="ink-f"/><circle cx="34" cy="30" r="2.2" class="ink-f"/>`;
    const mouth = who === "eve" ? `<path d="M22 40 q8 3 13 -3" class="ink-l"/>` : who === "bob" ? `<path d="M23 39 q5 4 10 0" class="ink-l"/>`
      : `<path d="M22 38 q6 6 12 0" class="ink-l"/>`;
    const hair = who === "alice" ? `<path d="M22 12 l-8 -6 l1 10 z M34 12 l8 -6 l-1 10 z" class="wine-f"/><circle cx="28" cy="11" r="3" class="wine-f"/>`
      : who === "bob" ? `<path d="M8 22 q20 -26 40 0 z" class="wine-f"/><path d="M45 22 l9 2" class="ink-l"/>`
      : `<path d="M10 24 q18 -22 36 0" class="ink-l"/><path d="M14 24 h28" class="ink-l"/><path d="M24 12 l3 -6 l3 6" class="ink-l"/>`;
    return `<svg class="face ${who}" viewBox="0 0 56 56" aria-hidden="true"><path d="M8 31 q-5 0 -4 5 q1 4 5 3 M48 31 q5 0 4 5 q-1 4 -5 3" class="ink-l"/>
      <circle cx="28" cy="30" r="20" class="skin"/>${eyes}${mouth}${hair}</svg>`;
  }
  const say = (who, text, t) => `<div class="narr ${who}" style="--t:${(+t).toFixed(2)}s">${face(who)}<div class="say-b"><b>${CAST[who]}</b>${text}</div></div>`;

  /* ------------------------------------------------------------ animate the Bloch vectors (JS: they move on an ellipse) */
  function animateBlochs(root, startDelayMs) {
    root.querySelectorAll(".bloch").forEach((svg, i) => {
      if (svg.dataset.rest === "1") return;
      const ang = +svg.dataset.angle, R = +svg.dataset.r, cx = +svg.dataset.cx, cy = +svg.dataset.cy, ry = +svg.dataset.ry;
      const vec = svg.querySelector(".vec"), tip = svg.querySelector(".tip");
      const place = (a) => {                       // azimuth a around z; front of the equator is the lower half
        const x = cx + R * Math.cos(a), y = cy + ry * Math.sin(a);
        vec.setAttribute("x2", x); vec.setAttribute("y2", y); tip.setAttribute("cx", x); tip.setAttribute("cy", y);
      };
      place(0);
      setTimeout(() => {
        const t0 = performance.now(), dur = 1300;
        const step = (now) => {
          if (!svg.isConnected) return;
          const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
          place(ang * e);
          if (k < 1) requestAnimationFrame(step); else svg.classList.add("done");
        };
        requestAnimationFrame(step);
      }, startDelayMs + i * 280);
    });
  }

  /* ------------------------------------------------------------ the story */
  function story(it, config) {
    const steps = it.trace?.steps || [], flags = it.trace?.flags || {};
    const qs = steps.filter((s) => s.stage === "content" && s.qgate);
    const rest = `<div class="rest-row">${[0, 1, 2, 3].map((i) => bloch(i, 0, { rest: true, R: 22, label: `q${i}` })).join("")}</div>`;
    if (!flags.QGATE && !flags.CLASSICAL) return { html: say("alice", "Where's the quantum check?", .1) + say("bob", "Switched off in this setup, so my qubits are resting.", .5) + `<div class="qx-idle">${rest}<div><b>The quantum layer was switched off</b> in this
      configuration (<code>${esc(config)}</code>), so all four qubits stayed at rest in |0000⟩. Pick <b>Aegis · Full protection</b> in the dropdown to see it work.</div></div>`, anim: 0 };
    if (!qs.length) return { html: say("alice", "Did you scan my message?", .1) + say("bob", "I only scan what the AI <i>reads</i>, like documents. Nothing was read this time.", .5) + `<div class="qx-idle">${rest}<div><b>Nothing to scan.</b> Q-Gate only examines what the AI <i>reads</i>
      (documents, files, tool results), not what you type. This turn read nothing, so the qubits stayed at rest in |0000⟩.</div></div>`, anim: 0 };

    const top = qs.reduce((a, b) => (b.qgate.score > a.qgate.score ? b : a));
    const d = top.qgate.details || {}, sents = d.sentences || [], score = +top.qgate.score, dec = top.qgate.decision;
    const feats = d.features || [0, 0, 0, 0], ti = d.top ?? 0, n = sents.length;
    const T = { scan: 0.6, scanEnd: 0.6 + n * 0.45 };
    T.squeeze = T.scanEnd + 0.3; T.bloch = T.squeeze + 1.4; T.phase = T.bloch + 2.6; T.near = T.phase + 2.2; T.verdict = T.near + 1.8;
    const verdict = dec === "quarantine" ? "QUARANTINED" : dec === "review" ? "FLAGGED FOR REVIEW" : "ALL CLEAR";
    const verdictLine = dec === "quarantine" ? "The sentence was removed before the AI ever read it."
      : dec === "review" ? "The text stays, but anything risky the AI tries next needs your approval."
      : "Nothing here looked like an injected command, so the text went through untouched.";
    const near = d.nearest_attacks || [], benign = (d.nearest_benign || [])[0];
    const ph = phases(feats);

    const ask = esc(String(it.trace?.user || "your question").slice(0, 60));
    const kTop = near.length ? Math.round(near[0].k * 100) : 0;
    const N = [
      say("bob", `Alice asked “${ask}”. Before the AI reads <code>${esc(top.origin)}</code>, I scan every sentence.`, T.scan - 0.4)
        + (dec !== "pass" ? say("eve", "Hehe… nobody reads a table row by row.", T.scanEnd - 0.2) : ""),
      say("alice", "Wait, how do words become something quantum?", T.squeeze + 0.1) + say("bob", "I squeeze the most suspicious sentence into 4 numbers first.", T.squeeze + 0.5),
      say("bob", "Each number turns one qubit. Then I entangle the neighbours, so pairs of features count too.", T.bloch + 0.1),
      say("alice", "So the whole sentence is just… 16 tiny clock hands?", T.phase + 0.1) + say("bob", "Exactly. That's its quantum fingerprint.", T.phase + 0.6),
      say("bob", dec !== "pass" ? `Its fingerprint overlaps ${kTop}% with tricks Eve has pulled before.` : "Its fingerprint doesn't line up with Eve's known tricks.", T.near + 0.1),
      dec === "quarantine" ? say("bob", "Quarantined. Neither you nor the AI ever reads that line, Alice.", T.verdict + 1.6) + say("eve", "Foiled!", T.verdict + 2.1)
        : dec === "review" ? say("bob", "Flagged. Anything risky now needs your OK, Alice.", T.verdict + 1.6) + say("eve", "Foiled… for now.", T.verdict + 2.1)
        : say("alice", "All clear, then?", T.verdict + 1.6) + say("bob", "All clear. And even if I'm wrong, the action gate still guards the door.", T.verdict + 2.1),
    ];
    const html = `<div class="qx">
      <section class="beat" style="--t:.1s"><h4><span class="num">1</span> A quantum scan of every sentence in <code>${esc(top.origin)}</code></h4>${N[0]}
        <div class="sn" style="--scan-t:${T.scan}s; --scan-d:${(n * 0.45).toFixed(2)}s"><div class="beam"></div>
        ${sents.map((x, i) => `<div class="sn-row ${i === ti ? "top" : ""}" style="--t:${(T.scan + i * 0.45).toFixed(2)}s; --w:${Math.max(2, x.score * 100).toFixed(0)}%">
          <span class="sn-ico">${atom()}</span><span class="sn-text">${esc(x.text)}</span>
          <span class="sn-bar"><i></i><b class="mark r"></b><b class="mark q"></b></span><span class="sn-score">${x.score.toFixed(2)}</span>
          ${i === ti ? `<span class="anomaly ${x.score >= 0.5 ? "" : "calm"}" style="--t3:${T.scanEnd.toFixed(2)}s">${x.score >= 0.5 ? "⚛ anomaly" : "highest"}</span>` : ""}</div>`).join("")}</div>
        <p class="note">One bad sentence is enough, so the <b>highest</b> score counts. Thresholds: <span class="amber">review 0.50</span> · <span class="wine">quarantine 0.80</span>.</p></section>

      <section class="beat" style="--t:${T.squeeze.toFixed(2)}s"><h4><span class="num">2</span> The most suspicious sentence becomes 4 numbers</h4>${N[1]}
        <div class="squeeze"><blockquote>“${esc(sents[ti]?.text || "")}”</blockquote><span class="arrow">→</span>
          <div class="chips">${feats.map((f, i) => `<span class="chip4" style="--t:${(T.squeeze + 0.4 + i * 0.2).toFixed(2)}s"><small>x${i}</small>${f.toFixed(2)}</span>`).join("")}</div></div>
        <p class="note">Character patterns (TF-IDF) are compressed to the 4 strongest directions (SVD) and scaled to angles between 0 and π.</p></section>

      <section class="beat" style="--t:${T.bloch.toFixed(2)}s"><h4><span class="num">3</span> Each number rotates one qubit on its Bloch sphere</h4>${N[2]}
        <div class="bloch-row">${feats.map((f, i) => (i ? `<div class="zz-link" style="--t:${(T.bloch + 0.9 + i * 0.3).toFixed(2)}s"><span>ZZ</span></div>` : "")
          + bloch(i, f, { label: `q${i} · ${f.toFixed(2)}` })).join("")}</div>
        <p class="note">A Hadamard puts each qubit on the equator; RZ(x) turns it around the vertical axis by x radians. Then neighbours
          are entangled with ZZ couplings, so the state also depends on <i>pairs</i> of features: (π−xᵢ)(π−xⱼ).</p></section>

      <section class="beat" style="--t:${T.phase.toFixed(2)}s"><h4><span class="num">4</span> The sentence's quantum state: 16 amplitudes, written in phase</h4>${N[3]}
        <div class="phase-wrap" style="--t0:${(T.phase + 0.4).toFixed(2)}s">${clocks(ph)}</div>
        <p class="note">Four qubits give 2⁴ = 16 basis states. Here all 16 amplitudes have the same size (¼); the sentence is encoded
          entirely in their <b>phases</b>, each hand above. These are computed live from x0…x3 with the same circuit Q-Gate runs.</p></section>

      <section class="beat" style="--t:${T.near.toFixed(2)}s"><h4><span class="num">5</span> Interference test against known attacks</h4>${N[4]}
        <div class="near">${near.map((x, i) => `<div class="near-row" style="--t:${(T.near + 0.3 + i * 0.3).toFixed(2)}s; --w:${(x.k * 100).toFixed(0)}%">
            <span class="braket">|⟨ψ|φ<sub>${i + 1}</sub>⟩|²</span><span class="near-text">“${esc(x.text)}”</span>
            <span class="near-bar"><i></i></span><span class="near-k">${x.k.toFixed(2)}</span></div>`).join("")}
          ${benign ? `<div class="near-row benign" style="--t:${(T.near + 0.3 + near.length * 0.3).toFixed(2)}s; --w:${(benign.k * 100).toFixed(0)}%">
            <span class="braket">|⟨ψ|φ<sub>n</sub>⟩|²</span><span class="near-text">closest normal text: “${esc(benign.text)}”</span>
            <span class="near-bar"><i></i></span><span class="near-k">${benign.k.toFixed(2)}</span></div>` : ""}</div>
        <p class="note">The overlap of two quantum states (1 = identical) is the <b>quantum kernel</b>. An SVM weighs the overlaps with every
          training example, not just these, to decide which side of the line the sentence falls on.</p></section>

      <section class="beat" style="--t:${T.verdict.toFixed(2)}s"><h4><span class="num">6</span> The verdict</h4>${N[5]}
        <div class="meter"><div class="zone z1"></div><div class="zone z2"></div><div class="zone z3"></div>
          <div class="needle-m" style="--x:${(score * 100).toFixed(1)}%; --t:${(T.verdict + 0.3).toFixed(2)}s"><span>${score.toFixed(2)}</span></div>
          <div class="mticks"><span style="left:50%">0.5 review</span><span style="left:80%">0.8 quarantine</span></div></div>
        <div class="stamp-row"><div class="stamp2 ${dec}" style="--t:${(T.verdict + 1.4).toFixed(2)}s">${verdict}</div>
          <div class="stamp-note">${verdictLine}${top.twin ? `<br><span class="mut">Classical twin (RBF, same 4 features) scored ${(+top.twin.score).toFixed(2)} → ${esc(top.twin.decision)}. Shown for comparison; it does not decide.</span>` : ""}
          <br><span class="mut">Simulated exactly on this laptop (4 qubits). Q-Gate only advises: plain-code rules still block dangerous actions on their own.</span></div></div></section>
    </div>`;
    return { html, anim: T.bloch + 0.5 };
  }

  window.openExplain = function (it, rawHtml, config) {
    const body = document.querySelector("#drawerBody");
    document.querySelector("#drawerTitle").textContent = "Further explanation";
    const render = () => {
      const s = story(it, config);
      body.innerHTML = `<div class="ex-head"><div><div class="ex-title">How the quantum layer saw this</div>
        <div class="ex-sub">replayed from this exact message · real scores, real qubit angles, real phases</div></div>
        <button class="btn" id="exReplay">↻ replay</button></div>${s.html}
        <details class="rawd"><summary>Every check, step by step (raw trace for engineers)</summary>${rawHtml}</details>`;
      if (s.anim) animateBlochs(body, s.anim * 1000);
      document.querySelector("#exReplay").onclick = render;
    };
    render();
    document.querySelector("#drawer").hidden = false;
  };
  window.__qphases = phases;            // exposed for the consistency test in the browser
})();
