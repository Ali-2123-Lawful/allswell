// Simulated Alexa+ experience: questions go to /api/ask, which answers by
// calling the Allswell MCP server. Voice in/out uses the browser Web Speech API.
(() => {
  const $ = (id) => document.getElementById(id);
  const log = $("log"), input = $("q"), orb = $("orb"), status = $("status");

  const STATUS = {
    idle: "Ask about Mum's day. Tap the mic or type.",
    listening: "Listening…",
    thinking: "Checking Allswell…",
    speaking: "Speaking…",
  };
  function setState(state) {
    orb.dataset.state = state;
    status.textContent = STATUS[state];
  }

  function addMsg(role, text, call) {
    const li = document.createElement("li");
    li.className = "msg " + role;
    const p = document.createElement("p");
    p.textContent = text;
    li.appendChild(p);
    if (call && call.tool) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tool";
      btn.textContent = "MCP tool · " + call.tool + '(person: "' + call.arguments.person + '")';
      const pre = document.createElement("pre");
      pre.hidden = true;
      pre.textContent = JSON.stringify(call.result, null, 2);
      btn.addEventListener("click", () => { pre.hidden = !pre.hidden; });
      li.append(btn, pre);
    }
    log.appendChild(li);
    li.scrollIntoView({ behavior: "smooth", block: "end" });
  }

  function say(text) {
    if (!$("voice").checked || !("speechSynthesis" in window)) { setState("idle"); return; }
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.onstart = () => setState("speaking");
    u.onend = u.onerror = () => setState("idle");
    speechSynthesis.speak(u);
  }

  async function ask(question) {
    question = question.trim();
    if (!question) return;
    addMsg("user", question);
    input.value = "";
    setState("thinking");
    try {
      const r = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const d = await r.json();
      addMsg("assistant", d.reply, d);
      say(d.reply);
    } catch (e) {
      addMsg("assistant", "Sorry, I couldn't reach Allswell just now.");
      setState("idle");
    }
  }

  $("form").addEventListener("submit", (e) => { e.preventDefault(); ask(input.value); });
  $("chips").addEventListener("click", (e) => {
    if (e.target.tagName === "BUTTON") ask(e.target.textContent);
  });

  // Voice input (Chrome / Edge). Hidden where the browser has no recognizer.
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (Recognition) {
    const rec = new Recognition();
    rec.lang = navigator.language || "en-US";
    rec.interimResults = false;
    rec.onstart = () => setState("listening");
    rec.onresult = (e) => ask(e.results[0][0].transcript);
    rec.onerror = rec.onend = () => { if (orb.dataset.state === "listening") setState("idle"); };
    $("mic").addEventListener("click", () => {
      if ("speechSynthesis" in window) speechSynthesis.cancel();
      try { rec.start(); } catch (e) { /* already listening */ }
    });
  } else {
    $("mic").hidden = true;
  }

  // Demo scenario switcher, so the whole demo can run from this one screen.
  async function loadScenarios() {
    const s = await (await fetch("/api/state")).json();
    const sel = $("scenario");
    sel.innerHTML = "";
    for (const [key, label] of Object.entries(s.scenarios)) {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = label;
      opt.selected = key === s.scenario;
      sel.appendChild(opt);
    }
  }
  $("scenario").addEventListener("change", async (e) => {
    await fetch("/api/scenario/" + e.target.value, { method: "POST" });
    addMsg("note", "Demo: today is now “" + e.target.selectedOptions[0].textContent + "”.");
  });

  setState("idle");
  addMsg("assistant", "Hi, I'm Allswell. Ask me how Mum's day is going.");
  loadScenarios();
})();
