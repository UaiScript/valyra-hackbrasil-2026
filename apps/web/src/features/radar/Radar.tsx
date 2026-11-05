import type { DemoDataset, ProfileId } from '../../shared/types/domain';
import { PageHeading } from '../../shared/components/Primitives';
import { Icon } from '../../shared/components/Icon';
import { profiles } from '../workspace/profiles';

export function Radar({
  data,
  profile,
  interests,
  onInterestsChange,
}: {
  data: DemoDataset;
  profile: ProfileId;
  interests: string[];
  onInterestsChange: (interests: string[]) => void;
}) {
  const events = data.radar.filter((event) => interests.includes(event.topic));
  return (
    <>
      <PageHeading
        title="Radar econômico"
        description={
          profile === 'personal'
            ? 'Contexto econômico para acompanhar junto ao planejamento pessoal.'
            : 'Contexto econômico relacionado às exposições da operação.'
        }
      />
      <div className="radar-disclaimer">
        <Icon name="info" size={18} />
        <p>
          <strong>Cenários fictícios.</strong> Exemplos ilustrativos, sem fontes verificadas ou IA
          conectada. Não alteram seus lançamentos.
        </p>
      </div>
      <fieldset className="interests-fieldset">
        <legend>{profiles[profile].interests}</legend>
        <div className="interest-options">
          {data.interests.map((interest) => (
            <label key={interest}>
              <input
                type="checkbox"
                checked={interests.includes(interest)}
                onChange={() =>
                  onInterestsChange(
                    interests.includes(interest)
                      ? interests.filter((item) => item !== interest)
                      : [...interests, interest],
                  )
                }
              />
              <span>{interest}</span>
            </label>
          ))}
        </div>
        <p className="panel-footnote">Preferências da sessão, separadas por perfil.</p>
      </fieldset>
      <div className="radar-list-header">
        <h2>Cenários em acompanhamento</h2>
        <span className="result-count" role="status" aria-live="polite">
          {events.length} {events.length === 1 ? 'exemplo selecionado' : 'exemplos selecionados'}
        </span>
      </div>
      <div className="radar-list">
        {events.map((event) => (
          <article className="radar-event" key={event.id}>
            <div className="radar-event-content">
              <div className="radar-event-meta">
                <span className="event-topic">{event.topic}</span>
                <span>{event.region}</span>
                <span>Origem: exemplo ilustrativo</span>
              </div>
              <h2>{event.title}</h2>
              <p className="event-summary">{event.summary}</p>
              <p className="event-relation">
                <strong>
                  {profile === 'personal' ? 'Relação com seu plano' : 'Relação com a operação'}:
                </strong>{' '}
                {event.context}
              </p>
              <details>
                <summary>
                  Entender o contexto
                  <Icon name="chevron" size={16} />
                </summary>
                <div className="event-detail">
                  <section>
                    <h3>Contexto</h3>
                    <p>
                      {event.region}. Este é um cenário fictício sobre{' '}
                      {event.topic.toLocaleLowerCase('pt-BR')}, apresentado para explorar perguntas
                      de planejamento.
                    </p>
                  </section>
                  <section>
                    <h3>Possível impacto · hipótese</h3>
                    <p>{event.premise}</p>
                  </section>
                  <section>
                    <h3>Limitações e evidências</h3>
                    <p>{event.limitation}</p>
                    <p>Exemplo ilustrativo. Não há fonte verificada para este evento fictício.</p>
                    <p>
                      Explicação editorial, sem análise real de IA. Nenhum impacto é aplicado
                      automaticamente ao financeiro.
                    </p>
                  </section>
                </div>
              </details>
            </div>
          </article>
        ))}
        {events.length === 0 && (
          <div className="empty-state">
            <h2>Nenhum tema selecionado</h2>
            <p>
              Selecione um {profile === 'personal' ? 'tema de interesse' : 'tipo de exposição'}{' '}
              acima para consultar os cenários.
            </p>
            <button
              type="button"
              className="button button-subtle"
              onClick={() => onInterestsChange([...data.interests])}
            >
              Selecionar todos os temas
            </button>
          </div>
        )}
      </div>
      <p className="panel-footnote">
        Fontes verificadas e explicações de IA com evidências fazem parte das próximas etapas, após
        alinhamento da equipe.
      </p>
    </>
  );
}
