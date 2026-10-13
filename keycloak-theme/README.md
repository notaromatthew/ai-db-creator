# Tema di accesso TecnIA per Keycloak

Tema per il tipo **login** (accesso, registrazione, recupero password). Contiene solo CSS con i token del design system
(`frontend/src/index.css`, chiaro e scuro in base al sistema), il marchio, e i testi in italiano e inglese. Nessun
template `.ftl`: eredita quelli del tema `keycloak`.

```
keycloak-theme/tecnia/login/
  theme.properties                 parent=keycloak, stili, lingue it/en
  resources/css/tecnia.css         token, scheda in vetro, pulsanti a pillola, focus visibile
  resources/img/                   marchio e favicon
  messages/messages_{it,en}.properties   testi e consenso al trattamento dei dati
```

## Montarlo su Coolify

1. Nel servizio Keycloak di Coolify aggiungi uno **storage** (bind mount o volume) con destinazione
   `/opt/keycloak/themes`. Con un bind mount copia la cartella `keycloak-theme/tecnia` dentro la sorgente, in modo
   che sul server esista `<sorgente>/tecnia/login/theme.properties`. Con un volume, copia i file dentro con
   `docker cp keycloak-theme/tecnia <container>:/opt/keycloak/themes/`.
2. Riavvia Keycloak (i temi si leggono all'avvio; in modalita' sviluppo con `--spi-theme-cache-themes=false` basta ricaricare).
3. Verifica in console: Realm settings > Themes > Login theme deve elencare `tecnia`.

## Attivarlo nel realm

Lo fa lo script di setup del backend quando la variabile d'ambiente dell'app e' impostata:

```
KEYCLOAK_LOGIN_THEME=tecnia
```

Imposta la variabile **solo dopo** aver montato il tema: finche' la cartella non e' presente sul server lascia la
variabile vuota, cosi' il realm resta sul tema predefinito (l'attivazione condizionata e' compito dello script di setup
del backend, non di questa cartella). In alternativa si seleziona a mano da Realm settings > Themes.

## Consenso al trattamento dei dati

I testi (`termsTitle`, `termsText`, `acceptTerms`) sono nei file dei messaggi. Perche' la casella compaia in registrazione:

1. Authentication > Required actions: abilita **Terms and Conditions**.
2. Authentication > flusso **registration** > *registration form*: aggiungi il passo **Terms and conditions** (se la tua
   versione di Keycloak lo offre) e impostalo come *Required*. In ogni caso, con l'azione richiesta abilitata la persona
   vede e deve accettare i termini al primo accesso; Keycloak registra data e ora dell'accettazione sull'utente.
3. Il testo dell'informativa rimanda a `https://tecniaweb.it/privacy`: la versione definitiva e' da fornire da TecnIA.

## Note e limiti

- Il tema e' scritto per il tema genitore `keycloak` (Keycloak 24-26). Se il tuo Keycloak usa il genitore `keycloak.v2`
  per il login, cambia `parent` in `theme.properties`: i selettori PatternFly 5 sono gia' coperti dal CSS.
- Non e' stato provato su un Keycloak reale: controlla a occhio accesso, registrazione e password dimenticata,
  in chiaro e in scuro, prima di dichiararlo pronto.
- I font Geist e Inter vengono dal sistema o dal browser; se non presenti si usa il carattere di sistema.
