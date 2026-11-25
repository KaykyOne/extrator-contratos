const formulario = document.querySelector(".formulario");
if (formulario) {
  const texto = document.querySelector("#texto");
  const estrategia = document.querySelector("#estrategia");
  const offline = document.querySelector("#offline");
  const extrair = document.querySelector("#botao-extrair");

  function carregar(botao, metodo, usarCache) {
    texto.value = botao.dataset.exemplo;
    estrategia.value = metodo;
    offline.checked = usarCache;
    texto.focus();
  }

  document.querySelector("#exemplo").addEventListener("click", evento => {
    carregar(evento.currentTarget, "few-shot", true);
  });
  document.querySelector("#exemplo-dataset").addEventListener("click", evento => {
    carregar(evento.currentTarget, "baseline", false);
  });
  formulario.addEventListener("submit", () => {
    extrair.disabled = true;
    extrair.textContent = "Extraindo…";
  });
  window.addEventListener("pageshow", () => {
    extrair.disabled = false;
    extrair.innerHTML = 'Extrair campos <span aria-hidden="true">→</span>';
  });

  const copiar = document.querySelector("#copiar-json");
  copiar?.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(document.querySelector("#dados-json").textContent);
      copiar.textContent = "JSON copiado";
    } catch {
      copiar.textContent = "Selecione o JSON para copiar";
    }
  });
}

const controles = document.querySelector("#controles-avaliacao");
if (controles) {
  const botoes = [...controles.querySelectorAll("[data-avaliar]:not(:disabled)")];
  const painel = document.querySelector("#andamento");
  const progresso = document.querySelector("#progresso");
  const mensagem = document.querySelector("#status-avaliacao");
  let acompanhar = false;

  function bloquear(bloqueado) {
    botoes.forEach(botao => { botao.disabled = bloqueado; });
  }

  function exibir(estado) {
    painel.hidden = false;
    progresso.max = estado.total || 1;
    progresso.value = estado.concluidos;
    mensagem.textContent = estado.mensagem;
  }

  async function consultar() {
    try {
      const resposta = await fetch(controles.dataset.endpoint, { cache: "no-store" });
      if (!resposta.ok) throw new Error("Status indisponível");
      const estado = await resposta.json();
      if (estado.situacao === "executando") {
        acompanhar = true;
        bloquear(true);
        exibir(estado);
        setTimeout(consultar, 800);
      } else if (acompanhar && estado.situacao === "concluida") {
        exibir(estado);
        window.location.reload();
      } else if (estado.situacao === "erro") {
        bloquear(false);
        exibir(estado);
      }
    } catch {
      if (acompanhar) {
        mensagem.textContent = "Reconectando ao servidor da avaliação…";
        setTimeout(consultar, 1800);
      }
    }
  }

  botoes.forEach(botao => botao.addEventListener("click", async () => {
    bloquear(true);
    try {
      const resposta = await fetch(controles.dataset.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ offline: botao.dataset.avaliar === "cache" }),
      });
      const estado = await resposta.json();
      if (resposta.status === 409) {
        acompanhar = true;
        consultar();
        return;
      }
      if (!resposta.ok) throw new Error(estado.erro || "Não foi possível iniciar a avaliação.");
      acompanhar = true;
      exibir(estado);
      consultar();
    } catch (erro) {
      acompanhar = false;
      bloquear(false);
      painel.hidden = false;
      mensagem.textContent = erro.message;
    }
  }));

  consultar();
}
