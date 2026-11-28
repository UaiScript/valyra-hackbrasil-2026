import type { FC } from 'react';
import { useEffect, useRef } from 'react';
import { Sparkles } from 'lucide-react';
import { ChatBody, questionFromHref, useValyraChat } from '../ValyraChat';

/** Tela cheia da Valyra AI: mesma conversa da barra lateral, com mais espaço. */
export const AskValyra: FC = () => {
  const { account, ask, closePanel } = useValyraChat();

  // Na tela cheia a barra lateral seria redundante.
  useEffect(() => { closePanel(); }, [closePanel]);

  // Pergunta vinda de um link direto (#/app/valyra-ai?q=...): envia assim que a conta carrega.
  const prefilled = useRef(false);
  useEffect(() => {
    if (prefilled.current || !account) return;
    const q = questionFromHref(window.location.hash);
    if (q) {
      prefilled.current = true;
      ask(q);
    }
  }, [account, ask]);

  return (
    <div className="cx-ai">
      <section className="cx-ai__intro">
        <span className="cx-ai__orb" aria-hidden="true"><Sparkles size={22} /></span>
        <div>
          <h2>Pergunte ao Valyra</h2>
          <p>A IA lê as evidências calculadas para a sua conta (saldo, transações, recorrências, projeção) e explica em linguagem simples. Ela <strong>não cria números</strong>: cada valor da resposta aparece abaixo com origem e período.</p>
        </div>
      </section>
      <ChatBody />
    </div>
  );
};
