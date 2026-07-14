# Crypto Opportunity Monitor

Monitora Reddit + CoinGecko e manda alerta push no seu iPhone quando detecta
uma possível oportunidade de valorização de curto prazo. 100% heurístico
(sem IA/LLM), então roda de graça e sem limite de uso.

## Passo a passo (uns 10 minutos, tudo grátis)

### 1. Instale o app de notificação no iPhone
- Baixe **ntfy** na App Store (gratuito): https://apps.apple.com/app/ntfy/id1625396347
- Abra o app, toque em "+" e crie/assine um tópico com um nome único e difícil
  de adivinhar, por exemplo: `xpto-cripto-alertas-9f3k2`
  (qualquer pessoa que souber esse nome recebe seus alertas, então não use
  algo óbvio tipo "cripto123")

### 2. Edite o arquivo `monitor.py`
Troque a linha:
```python
NTFY_TOPIC = "SEU-TOPICO-UNICO-AQUI-troque-isso"
```
pelo nome do tópico que você criou no app.

### 3. Suba os arquivos para um repositório no GitHub
1. Crie uma conta no GitHub (se ainda não tiver): https://github.com
2. Crie um repositório novo, **público** (para ter minutos de Actions ilimitados),
   ex: `crypto-monitor`
3. Envie esta pasta inteira para o repositório (pelo site do GitHub mesmo,
   arrastando os arquivos, ou via `git push` se preferir linha de comando)

### 4. Ative o GitHub Actions
- Vá na aba **Actions** do repositório e habilite os workflows
- O monitor já vai começar a rodar sozinho a cada 15 minutos
- Você pode forçar uma execução manual em Actions → Crypto Opportunity Monitor → "Run workflow"

### 5. Pronto
Quando o script encontrar uma moeda com score acima do limiar, você recebe
uma notificação no iPhone com: nome da moeda, variação de preço, volume e
quantidade de menções recentes no Reddit.

## Ajustando a sensibilidade

No topo de `monitor.py`:
- `SCORE_THRESHOLD` — menor = mais alertas (e mais ruído)
- `MIN_VOLUME_USD` / `MIN_MARKET_CAP_USD` — filtros de liquidez para evitar
  moedas fáceis de manipular
- `ALERT_COOLDOWN_SECONDS` — tempo mínimo entre alertas repetidos da mesma moeda
- `SUBREDDITS` — adicione ou remova fóruns monitorados

## Limitações importantes

- Isso é uma ferramenta de **triagem por sinais**, não uma previsão confiável.
  "Menções em alta" e "variação de preço" não garantem valorização futura.
- Mercado cripto é extremamente volátil; moedas pequenas ("microcaps") viram
  alvo fácil de pump-and-dump, mesmo passando pelos filtros de liquidez.
- Não é recomendação de investimento. Sempre faça sua própria análise antes
  de qualquer decisão financeira.
