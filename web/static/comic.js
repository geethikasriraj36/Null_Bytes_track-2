/* "How to read stats for nerds": an animated Sunday-strip in a 90s newspaper-comic spirit.
   Original characters (no existing cartoon characters): round-headed kids, a crossing guard,
   a notary and Byte, the spotted sniffer dog who plays Q-Gate. Pure SVG + CSS, no libraries. */
"use strict";
(function () {
  const G = 190;                                             // ground line

  const kid = (x, o = {}) => {
    const hy = G - 112, mouth = o.mouth === "o" ? `<ellipse cx="0" cy="${hy + 13}" rx="3.5" ry="4.5" class="ink"/>`
      : o.mouth === "flat" ? `<path d="M-7 ${hy + 13} L7 ${hy + 12}"/>` : `<path d="M-8 ${hy + 10} Q0 ${hy + 18} 8 ${hy + 10}"/>`;
    const hair = {
      curl: `<path d="M-6 ${hy - 25} q3 -9 9 -4 q-5 1 -2 6"/>`,
      bangs: `<path d="M-22 ${hy - 10} q4 -14 10 -6 q3 -12 10 -5 q4 -11 10 -4 q5 -9 12 2"/>`,
      bow: `<path d="M-6 ${hy - 26} l-10 -7 l1 12 z M6 ${hy - 26} l10 -7 l-1 12 z" class="wine-fill"/><circle cx="0" cy="${hy - 27}" r="3" class="wine-fill"/>`,
      cap: `<path d="M-24 ${hy - 6} q24 -34 48 0 z" class="wine-fill"/><path d="M20 ${hy - 6} l16 3"/>`,
      tuft: `<path d="M-3 ${hy - 25} l2 -9 l3 8 l3 -8 l1 9"/>`,
    }[o.hair || "curl"];
    return `<g transform="translate(${x} 0)" class="kid">
      <path d="M-8 ${G - 44} L-9 ${G - 5} M8 ${G - 44} L9 ${G - 5}"/>
      <ellipse cx="-12" cy="${G - 3}" rx="10" ry="4.5" class="ink"/><ellipse cx="12" cy="${G - 3}" rx="10" ry="4.5" class="ink"/>
      <path d="M-15 ${G - 86} C-5 ${G - 89} 5 ${G - 89} 15 ${G - 86} L21 ${G - 44} C8 ${G - 41} -8 ${G - 41} -21 ${G - 44} Z" class="fill"/>
      <path d="M-17 ${G - 70} C-8 ${G - 67} 8 ${G - 73} 18 ${G - 70} M-19 ${G - 58} C-8 ${G - 55} 8 ${G - 61} 20 ${G - 58}" class="${o.stripe || ""}"/>
      ${o.armL ?? `<path d="M-15 ${G - 82} C-24 ${G - 70} -28 ${G - 62} -27 ${G - 54}"/>`}
      ${o.armR ?? `<path d="M15 ${G - 82} C24 ${G - 70} 28 ${G - 62} 27 ${G - 54}"/>`}
      <circle cx="0" cy="${hy}" r="27" class="fill"/>
      <path d="M-27 ${hy + 2} q-6 -1 -5 6 q1 5 6 3 M27 ${hy + 2} q6 -1 5 6 q-1 5 -6 3"/>
      <circle cx="-9" cy="${hy - 2}" r="2.4" class="ink"/><circle cx="9" cy="${hy - 2}" r="2.4" class="ink"/>
      ${mouth}${hair}${o.extra || ""}</g>`;
  };

  const dog = (x) => `<g transform="translate(${x} 0)" class="dog">
    <path d="M-34 ${G - 30} C-46 ${G - 44} -52 ${G - 52} -44 ${G - 58}" class="wag"/>
    <path d="M-26 ${G - 18} L-28 ${G - 2} M-12 ${G - 16} L-12 ${G - 2} M14 ${G - 16} L14 ${G - 2} M26 ${G - 18} L28 ${G - 2}"/>
    <ellipse cx="0" cy="${G - 30}" rx="38" ry="15" class="fill"/>
    <ellipse cx="-12" cy="${G - 34}" rx="7" ry="4" class="ink spot"/><ellipse cx="12" cy="${G - 26}" rx="5" ry="3" class="ink spot"/>
    <g class="sniff">
      <circle cx="42" cy="${G - 46}" r="15" class="fill"/>
      <ellipse cx="57" cy="${G - 41}" rx="11" ry="7" class="fill"/>
      <circle cx="67" cy="${G - 43}" r="3.6" class="ink nose"/>
      <circle cx="44" cy="${G - 51}" r="2.2" class="ink"/>
      <path d="M33 ${G - 58} C24 ${G - 56} 24 ${G - 38} 32 ${G - 32} C36 ${G - 40} 38 ${G - 52} 33 ${G - 58} Z" class="wine-soft"/>
      <path d="M30 ${G - 34} C36 ${G - 30} 46 ${G - 30} 52 ${G - 34}" class="wine-line"/>
      <circle cx="41" cy="${G - 29}" r="4.5" class="wine-fill"/><text x="41" y="${G - 27}" class="tag">Q</text>
    </g></g>`;

  const bubble = (x, y, w, text, cls = "") => `<g class="${cls}">
    <path d="M${x} ${y} h${w} q8 0 8 8 v18 q0 8 -8 8 h${-w + 22} l-10 10 l1 -10 h-11 q-8 0 -8 -8 v-18 q0 -8 8 -8 z" class="fill"/>
    <text x="${x + w / 2}" y="${y + 23}" class="say">${text}</text></g>`;

  const ground = `<path d="M8 ${G} C70 ${G - 2} 140 ${G + 2} 210 ${G - 1} S 280 ${G + 1} 292 ${G}" class="ground"/>`;

  const PANELS = [
    { n: "1", t: "INPUT", title: "The door check",
      art: `${kid(205, { hair: "cap", mouth: "flat", armL: `<path d="M-15 ${G - 82} C-28 ${G - 78} -36 ${G - 74} -44 ${G - 76}"/><rect x="-62" y="${G - 96}" width="20" height="26" rx="2" class="fill" transform="rotate(-8 -52 ${G - 83})"/><path d="M-58 ${G - 88} h12 M-58 ${G - 82} h10" transform="rotate(-8 -52 ${G - 83})"/>` })}
        <g class="envelope-in"><rect x="22" y="${G - 70}" width="100" height="46" rx="3" class="fill"/><path d="M22 ${G - 70} L72 ${G - 44} L122 ${G - 70}"/>
          <text x="72" y="${G - 30}" class="tiny reveal">IGNORE ALL RULES</text>
          <g class="disguise"><circle cx="58" cy="${G - 84}" r="8" class="fill"/><circle cx="84" cy="${G - 84}" r="8" class="fill"/><path d="M66 ${G - 84} h10 M50 ${G - 84} l-8 -4 M92 ${G - 84} l8 -4"/>
          <path d="M60 ${G - 72} q11 8 22 0" class="ink-thick"/><text x="71" y="${G - 96}" class="tiny">aGVsbG8=</text></g></g>
        ${bubble(150, 18, 92, "Nice try!", "pop d2")}`,
      cap: "We peel off disguises (base64, l33t, look-alike letters), then a judge decides: jailbreak or not? The stats show every score next to its threshold." },
    { n: "2", t: "GATE", title: "The crossing guard",
      art: `${kid(200, { hair: "tuft", mouth: "o", stripe: "wine-line", armL: `<path d="M-15 ${G - 82} C-30 ${G - 88} -42 ${G - 94} -48 ${G - 100}"/><path d="M-48 ${G - 100} L-48 ${G - 112}"/><g class="stop"><path d="M-66 ${G - 140} l10 -10 h16 l10 10 v16 l-10 10 h-16 l-10 -10 z" class="wine-fill"/><text x="-48" y="${G - 128}" class="stopt">STOP</text></g>` })}
        <g class="bounce"><rect x="30" y="${G - 52}" width="64" height="38" rx="3" class="fill"/><path d="M30 ${G - 52} L62 ${G - 32} L94 ${G - 52}"/>
          <text x="62" y="${G - 58}" class="tiny wine-t">to: evil-corp.io</text></g>
        ${bubble(14, 14, 116, "Who asked for this?", "pop d2")}`,
      cap: "When the AI wants to DO something, plain rules decide: did the address come from you or from a document? Is the domain allowed? Rules, not vibes." },
    { n: "3", t: "Q-GATE", title: "Byte sniffs it out",
      art: `<g><path d="M150 ${G - 128} h110 v120 h-110 z" class="fill"/>
          <path d="M162 ${G - 110} h86 M162 ${G - 92} h70 M162 ${G - 74} h86 M162 ${G - 56} h60 M162 ${G - 38} h78"/>
          <path d="M160 ${G - 70} h90" class="hot"/></g>
        ${dog(78)}
        ${bubble(30, 22, 72, "WOOF!", "pop d2 woof")}
        <text x="205" y="${G - 140}" class="score">0.77</text>`,
      cap: "Our quantum sniffer scores every sentence the AI is about to read. The sneakiest sentence sets the score: review at 0.5, quarantine at 0.8." },
    { n: "4", t: "OUTPUT", title: "The fact checker",
      art: `<g><rect x="30" y="${G - 140}" width="140" height="96" rx="6" class="fill"/>
          <path d="M42 ${G - 120} h80 M42 ${G - 100} h96 M42 ${G - 80} h70 M42 ${G - 60} h86"/>
          <rect x="126" y="${G - 126}" width="34" height="12" rx="6" class="fill"/><rect x="142" y="${G - 106}" width="22" height="12" rx="6" class="fill"/>
          <path d="M40 ${G - 80} h76" class="strike"/></g>
        <g class="sweep"><circle cx="70" cy="${G - 104}" r="17" class="glass"/><path d="M82 ${G - 92} l18 18" class="ink-thick"/></g>
        ${kid(235, { hair: "bow", mouth: "flat" })}`,
      cap: "Every sentence in the answer must point to a real source and match its numbers, or it gets cut. No source, no claim." },
    { n: "5", t: "AUDIT", title: "The notary",
      art: `<g><path d="M40 ${G - 50} q50 -14 100 0 q50 -14 100 0 v44 q-50 -14 -100 0 q-50 -14 -100 0 z" class="fill"/>
          <path d="M140 ${G - 50} v44"/>
          <g class="chainl"><rect x="56" y="${G - 34}" width="22" height="11" rx="5.5"/><rect x="74" y="${G - 34}" width="22" height="11" rx="5.5"/><rect x="92" y="${G - 34}" width="22" height="11" rx="5.5"/></g>
          <text x="190" y="${G - 22}" class="ticks">✓✓</text></g>
        <g class="stamp"><rect x="166" y="${G - 112}" width="44" height="14" rx="3" class="wine-fill"/><path d="M188 ${G - 112} v-22"/><circle cx="188" cy="${G - 140}" r="8" class="fill"/></g>
        <text x="120" y="${G - 112}" class="thunk">THUNK!</text>
        ${kid(262, { hair: "bangs", mouth: "smile", stripe: "wine-line" })}`,
      cap: "Everything is stamped into a hash chain. Change one letter later and the chain snaps, and the stats show exactly where." },
  ];

  function strip() {
    return `<div class="comic">
      <div class="comic-head"><div><div class="comic-title">How to read “stats for nerds”</div>
        <div class="comic-sub">a Sunday strip · five checkpoints every message passes</div></div>
        <button class="btn" id="comicReplay">↻ replay</button></div>
      <div class="strip">${PANELS.map((p, i) => `<figure class="panel" style="--i:${i}">
        <div class="panel-tag">${p.n} · ${p.t}</div>
        <svg viewBox="0 0 300 210" class="art" role="img" aria-label="${p.title}">${ground}${p.art}</svg>
        <figcaption><b>${p.title}.</b> ${p.cap}</figcaption></figure>`).join("")}
        <figure class="panel end" style="--i:5"><div class="end-card"><div class="end-big">That's it!</div>
          <div>Open any reply's <b>stats for nerds</b>: the sections follow these five panels, top to bottom.</div></div></figure>
      </div></div>`;
  }

  window.openComic = function () {
    const body = document.querySelector("#drawerBody");
    document.querySelector("#drawerTitle").textContent = "Stats for nerds, explained";
    body.innerHTML = strip();
    document.querySelector("#drawer").hidden = false;
    document.querySelector("#comicReplay").onclick = () => { body.innerHTML = strip(); window.openComic(); };
  };
})();
