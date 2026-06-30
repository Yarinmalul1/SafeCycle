/* View: Chat - multi-turn conversation with the LLM contraception advisor.
   Opens when the user types into the free-text box on /entry, or when they
   open a past conversation from Profile. Stores everything in Supabase via
   /api/chat/* so a refresh / sign-in elsewhere can replay the whole thread.

   URL params:
     - new=1         start a fresh chat using state.session.rawInput as
                     the opening user message
     - id=<uuid>     reopen an existing chat by session id (read-only or
                     continue typing if not yet marked complete) */
import { state } from "../state.js";
import { router } from "../router.js";
import { api } from "../api.js";
import { escapeHtml } from "../util.js";
import { toast } from "../toast.js";

function bubble(role, content) {
  const cls = role === "user" ? "chat-bubble chat-bubble--user" : "chat-bubble chat-bubble--ai";
  // Preserve the model's newlines without enabling arbitrary HTML.
  const safe = escapeHtml(content).replace(/\n/g, "<br>");
  return `<div class="${cls}">${safe}</div>`;
}

function renderMessages(messages) {
  if (!messages || !messages.length) {
    return `<p class="muted" style="text-align:center">No messages yet.</p>`;
  }
  return messages.map((m) => bubble(m.role, m.content)).join("");
}

function scrollToBottom(thread) {
  // Defer so the new bubble is in the DOM and has a height.
  requestAnimationFrame(() => {
    thread.scrollTop = thread.scrollHeight;
  });
}

function setComposerEnabled(form, enabled) {
  form.querySelector("textarea").disabled = !enabled;
  form.querySelector("button[type=submit]").disabled = !enabled;
  form.querySelector("#chat-done-btn").disabled = !enabled;
}

export const ChatView = {
  render(params = {}) {
    if (!state.user?.userId) {
      router.go("/");
      return { title: "", html: "", showBack: false };
    }
    const isNew = params.new === "1";
    const sessionId = params.id || null;

    return {
      title: "Chat",
      html: `
        <div class="stack" style="gap:var(--space-2)">
          <h1 class="title">Ask SafeCycle</h1>
          <p class="muted">The advisor may ask a couple of follow-up questions
            before giving a final answer.</p>
        </div>

        <div id="chat-thread" class="chat-thread" aria-live="polite">
          <p class="muted" style="text-align:center">Starting your chat…</p>
        </div>

        <form id="chat-form" class="chat-composer" autocomplete="off">
          <label class="sr-only" for="chat-input">Your message</label>
          <textarea id="chat-input" class="textarea chat-composer__input"
            rows="2" placeholder="Type your message…"></textarea>
          <div class="chat-composer__actions">
            <button id="chat-done-btn" type="button" class="btn btn--ghost">Done</button>
            <button type="submit" class="btn btn--primary">
              <span class="material-symbols-outlined" aria-hidden="true">send</span>
              Send
            </button>
          </div>
        </form>
      `,
      async onMount(el) {
        const thread = el.querySelector("#chat-thread");
        const form = el.querySelector("#chat-form");
        const input = el.querySelector("#chat-input");
        const doneBtn = el.querySelector("#chat-done-btn");

        let currentSessionId = sessionId;
        let chatComplete = false;

        const render = (chat) => {
          thread.innerHTML = renderMessages(chat.messages);
          scrollToBottom(thread);
          chatComplete = !!chat.complete;
          if (chatComplete) {
            form.hidden = true;
          }
        };

        // Bootstrap: either start a new chat (with the rawInput the user
        // typed on /entry) or replay an existing one.
        if (isNew) {
          const opener = (state.session.rawInput || "").trim();
          if (!opener) {
            thread.innerHTML = `<p class="muted" style="text-align:center">No question to ask yet. Go back and type one.</p>`;
            form.hidden = true;
            return;
          }
          setComposerEnabled(form, false);
          const res = await api.startChat({ userId: state.user.userId, message: opener });
          setComposerEnabled(form, true);
          if (!res.ok) {
            thread.innerHTML = `<div class="card stack" style="gap:var(--space-2)">
              <strong>Couldn't start the chat</strong>
              <p class="muted">${escapeHtml(res.reason)}</p>
            </div>`;
            form.hidden = true;
            toast(res.reason);
            return;
          }
          currentSessionId = res.chat.session_id;
          // Clear the rawInput so refreshing /chat?new=1 doesn't restart.
          state.update({ rawInput: "" });
          render(res.chat);
        } else if (currentSessionId) {
          const res = await api.getChat(currentSessionId);
          if (!res.ok) {
            thread.innerHTML = `<div class="card stack" style="gap:var(--space-2)">
              <strong>Couldn't load this chat</strong>
              <p class="muted">${escapeHtml(res.reason)}</p>
            </div>`;
            form.hidden = true;
            return;
          }
          render(res.chat);
        } else {
          thread.innerHTML = `<p class="muted" style="text-align:center">No chat selected.</p>`;
          form.hidden = true;
          return;
        }

        // Send a turn: append the user's bubble immediately for snappy UX,
        // disable the composer while we wait, then replace with the server's
        // canonical transcript when the reply comes back.
        form.addEventListener("submit", async (e) => {
          e.preventDefault();
          const content = input.value.trim();
          if (!content || chatComplete) return;
          input.value = "";

          thread.insertAdjacentHTML("beforeend", bubble("user", content));
          thread.insertAdjacentHTML(
            "beforeend",
            `<div class="chat-bubble chat-bubble--ai chat-bubble--pending">…</div>`
          );
          scrollToBottom(thread);
          setComposerEnabled(form, false);

          const res = await api.sendChatMessage({
            sessionId: currentSessionId,
            content,
          });
          setComposerEnabled(form, true);

          if (!res.ok) {
            // Drop the pending placeholder and show a recoverable error.
            const pending = thread.querySelector(".chat-bubble--pending");
            if (pending) pending.remove();
            toast(res.reason || "Couldn't send your message.");
            return;
          }
          render(res.chat);
          input.focus();
        });

        doneBtn.addEventListener("click", async () => {
          setComposerEnabled(form, false);
          const res = await api.completeChat(currentSessionId);
          if (!res.ok) {
            setComposerEnabled(form, true);
            toast(res.reason || "Couldn't mark the chat done.");
            return;
          }
          chatComplete = true;
          form.hidden = true;
          toast("Saved to history.");
          router.go("/home");
        });
      },
    };
  },
};
