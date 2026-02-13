# Bilan exhaustif — Complex PDF Test & Chat (Option A)

## Conclusion courte

On a mis en place un **pipeline PDF → chunks → Meilisearch (embedder Mistral)**, puis le **chat natif Meilisearch (Option A)** en s’appuyant sur la **feature expérimentale** `chatCompletions`. Sur un PDF technique réel (paper Mixtral 8x7B), le système répond correctement à quatre questions ciblées (architecture, benchmarks, routing, français), avec **recherche hybride** (keyword + sémantique). La due diligence en sort renforcée : on a validé la stack sur un cas réaliste et identifié les contraintes (version, master key, baseUrl Mistral, pas de SDK chat dédié). Les difficultés rencontrées (panic, mauvais provider, 401) sont documentées et corrigées dans les scripts ; le bilan est **positif pour un PoC**, avec des réserves claires sur le caractère expérimental et la maturité opérationnelle.

---

## 1. Objectifs : pourquoi on a fait ça

### 1.1 Tester la phase experimental-features

- La doc Meilisearch qualifie le **chat** de feature **expérimentale** (`chatCompletions`), activable via `PATCH /experimental-features`.
- Objectif : vérifier en conditions réelles si cette feature est **utilisable** dans un scénario RAG (index de chunks, LLM Mistral), et si elle apporte une vraie valeur (réponses fondées sur les chunks, pas de hallucination grossière).
- Enjeu due diligence : savoir si on peut recommander ou non de s’appuyer sur cette brique pour un projet (avec les précautions qui s’imposent).

### 1.2 Voir les performances sur un vrai PDF

- Les tests “simple” (ex. `simple_sdk_test/`) utilisent des JSONs préconstruits ; ils ne valident pas le **parsing PDF**, le **chunking** ni le comportement sur **tableaux / sections / figures**.
- Objectif : utiliser un **PDF technique réel** (paper Mixtral of Experts, ~2,4 Mo, tableaux, benchmarks, formules, plusieurs sections) pour évaluer :
  - la chaîne **parse → normalize → chunk → index** ;
  - la **qualité de la recherche** (hybrid) et de la **réponse du chat** sur des questions précises (chiffres, nuances sémantiques, tableaux).
- Enjeu due diligence : répondre à la question “Meilisearch + Mistral, ça tient la route sur un document complexe ou pas ?”.

### 1.3 Répondre aux questions de la due diligence de base

Le repo est dédié à un **audit / due diligence Meilisearch + Mistral** (hybrid search, RAG). Ce qu’on a fait dans `complex_pdf_test/` contribue directement à :

| Question due diligence | Ce que le complex PDF test apporte |
|------------------------|------------------------------------|
| **Hybrid search en conditions réelles** | Index `pdf_chunks` avec embedder Mistral ; recherche hybride (keyword + semantic) utilisée par le chat ; script `search_chunks_for_query.py` pour inspecter les chunks retournés. |
| **RAG “clé en main” vs bricolage** | Option A (chat natif) = un seul appel API, Meilisearch gère retrieval + appel LLM ; on a mesuré que les réponses sont ancrées dans le document (4 questions ciblées validées). |
| **Maturité / risques des features expérimentales** | Activation `chatCompletions`, bugs rencontrés (panic sans master key, baseUrl obligatoire pour Mistral), absence de wrapper SDK chat : on documente le coût et les contournements. |
| **Qualité sur PDFs complexes** | Un vrai paper avec tableaux et sections ; validation que les chiffres (GSM8K, Humaneval, Table 4 FR) et les nuances (routing non spécialisé par domaine) sont correctement récupérés. |
| **Intégration Mistral (embedding + chat)** | Embedding Mistral pour les chunks ; chat configuré avec source Mistral + baseUrl pour éviter le routage vers OpenAI ; une seule stack cohérente. |

---

## 2. Ce qui a été mis en place (point par point)

### 2.1 Pipeline PDF → chunks → JSON

| Fichier | Rôle | Pourquoi |
|---------|------|----------|
| **parse_pdf.py** | Utilise **Docling** pour convertir le PDF en markdown (layout, tableaux, texte). | Avoir une représentation structurée du PDF pour chunker proprement (sections, paragraphes) au lieu de couper au caractère. |
| **normalize_elements.py** | Normalisation du texte (espaces, retours à la ligne) via regex. | Réduire le bruit et les variations d’espaces avant chunking et indexation. |
| **chunk_pdf.py** | Découpage par titres `##` / `###`, puis par taille (max_chars, overlap). | Éviter de couper au milieu d’une phrase ou d’un tableau ; garder des unités sémantiques (sections) quand c’est possible. |
| **build_documents.py** | Construit la liste de documents (chunks) au format cible. | Unifier le format (id, doc_id, chunk_text, title, page, element_type, source_file) pour l’export JSON et Meilisearch. |
| **schemas.py** | Définit `RawElement`, `Chunk`, `chunk_to_meilisearch_doc`. | Typage et cohérence des structures dans tout le pipeline. |
| **run_pipeline.py** | Orchestre parse → normalize → chunk → build → écriture JSON ; option `--load` pour pousser vers Meilisearch. | Un seul point d’entrée pour reproduire l’expérience et charger l’index. |

**Document de test :** `mistral-doc.pdf` (paper Mixtral of Experts).  
**Sortie :** `mistral-doc.chunks.json` (43 chunks). Observations déjà notées : premier chunk parfois bruit (noms d’auteurs), légendes de figures dans le texte, `page` souvent null ; on a gardé tel quel pour le rapport.

### 2.2 Chargement dans Meilisearch (index `pdf_chunks`)

| Fichier | Rôle | Pourquoi |
|---------|------|----------|
| **load_to_meilisearch.py** | Configure l’index `pdf_chunks` (searchable: `chunk_text`, `title` ; filterable: `doc_id`, `page`, etc.) et enregistre l’**embedder Mistral** (REST, dimensions 1024, documentTemplate pour l’embedding). Puis ajoute les documents. | Permettre la **recherche hybride** (keyword + semantic) ; les embeddings sont calculés côté Meilisearch via l’API Mistral. |

L’index est donc prêt pour la recherche full-text et sémantique, avec le même modèle Mistral que pour le chat.

### 2.3 Chat natif Meilisearch (Option A — experimental)

| Fichier | Rôle | Pourquoi |
|---------|------|----------|
| **setup_meilisearch_chat.py** | 1) Active la feature expérimentale `chatCompletions` (PATCH `/experimental-features`). 2) Configure l’index `pdf_chunks` pour le chat (description, documentTemplate Liquid, documentTemplateMaxBytes). 3) Crée/met à jour le workspace **mistral-pdf** (source Mistral, apiKey, **baseUrl** `https://api.mistral.ai/v1`, prompts système). | Sans ce setup, le chat n’existe pas (feature désactivée), l’index n’est pas “chat-aware”, et le LLM ne serait pas Mistral (sans baseUrl, Meilisearch a routé vers OpenAI dans nos tests). |
| **ask_chat.py** | Envoie une question en POST `/chats/mistral-pdf/chat/completions` (stream: true), parse le flux SSE (format OpenAI-like), affiche le contenu et gère les erreurs (events avec `error`). Option `--debug` pour inspecter la structure des chunks SSE. | Permettre d’interroger le document en langage naturel et d’obtenir une réponse synthétique au lieu de seulement une liste de hits. |
| **search_chunks_for_query.py** | Lance une **recherche hybride** (même paramètres que ce que le chat utilise en interne) sur `pdf_chunks` et affiche les chunks retournés (id, title, extrait chunk_text). | Comme le chat ne renvoie pas les sources (tools désactivés), ce script sert de **proxy** pour voir “quels chunks ont été (ou auraient été) envoyés au LLM”. |

**Mode de search effectivement utilisé par le chat :** **hybrid** (keyword + semantic, embedder `mistral`). Les chunks renvoyés au LLM sont ceux de cette recherche hybride, formatés selon le `documentTemplate` configuré dans le chat de l’index.

---

## 3. Difficultés observées (être critique)

### 3.1 Version et activation du chat

- **Meilisearch &lt; v1.15.1** : la route `/experimental-features` renvoie **400** pour `chatCompletions` (feature inexistante ou non activable). Il a fallu **mettre à jour l’image Docker** (v1.13 → v1.15.1).
- **Impact** : en prod ou en CI, il faut figer une version ≥ v1.15.1 et documenter la dépendance.

### 3.2 Panic côté serveur (Rust unwrap on None)

- En **v1.15** et **v1.15.1**, sans **master key** : le serveur **panic** (e.g. `chat_completions.rs:446`, `Option::unwrap()` on `None`) lors d’un appel à `/chat/.../completions`. La doc évoque une “Default Chat API Key” créée quand une master key est présente ; sans elle, le code suppose une clé et plante.
- **Contournement** : lancer Meilisearch avec une **master key** (≥ 16 caractères) et utiliser la **même valeur** dans `.env` (`MEILISEARCH_API_KEY`). On a rendu la clé **obligatoire** dans `setup_meilisearch_chat.py` et `ask_chat.py` pour le chat.
- **Critique** : une feature expérimentale ne devrait pas faire planter le processus ; c’est un risque pour la maturité.

### 3.3 Routage vers le mauvais provider (OpenAI au lieu de Mistral)

- Sans **baseUrl** dans le workspace, Meilisearch envoyait les requêtes chat vers **OpenAI** ; l’erreur renvoyée était “Incorrect API key... platform.openai.com” alors qu’on avait configuré une clé Mistral.
- **Contournement** : ajout explicite de **`baseUrl": "https://api.mistral.ai/v1"`** dans le workspace. Après re-setup, le chat a bien utilisé Mistral et renvoyé des réponses correctes.
- **Critique** : le comportement par défaut (sans baseUrl) est trompeur ; la doc pourrait mieux préciser que pour Mistral, fixer la baseUrl est fortement recommandé.

### 3.4 Outils du chat (Progress / Sources) désactivés

- L’envoi du paramètre **`tools`** (e.g. `_meiliSearchProgress`, `_meiliSearchSources`) provoquait un **panic** (unwrap on None) en v1.15. On a donc **retiré** `tools` du body dans `ask_chat.py`.
- **Conséquence** : pas de **sources** (chunks) dans la réponse du chat ; on ne voit pas explicitement “ce passage vient du chunk X”. Pour l’audit, on compense avec `search_chunks_for_query.py`.
- **Critique** : pour un usage “sérieux” (traçabilité, conformité), l’affichage des sources est important ; la stabilité des tools expérimentaux est à surveiller.

### 3.5 Erreurs de script et de configuration

- **401 sur GET /version** : dans `setup_meilisearch_chat.py`, l’appel à `/version` ne passait pas les **headers** (Authorization). Corrigé en ajoutant `headers=headers`.
- **Clé API vide ou incorrecte** : si la master key fait &lt; 16 caractères, Meilisearch en génère une autre et l’affiche ; si `.env` garde l’ancienne, **403 invalid_api_key**. Il a fallu documenter “même valeur dans docker run et MEILISEARCH_API_KEY”, et ajouter un `.strip()` sur la clé dans `config/settings.py` pour éviter les espaces parasites.
- **Chargement du .env** : selon le répertoire de travail, `load_dotenv()` ne trouvait pas le `.env`. On a ajouté **`load_dotenv(PROJECT_ROOT / ".env")`** dans `setup_meilisearch_chat.py` et `ask_chat.py` pour forcer le chargement depuis la racine du projet.

### 3.6 Affichage (encodage)

- En sortie terminal, les caractères accentués peuvent s’afficher en **mojibake** (e.g. `Ã©` au lieu de `é`). Le contenu reçu est bien en UTF-8 ; le problème est côté environnement d’affichage (terminal/IDE). Pas de correctif dans le code pour l’instant.

---

## 4. Procédure suivie (comment on a procédé)

1. **Pipeline PDF** : mise en place de parse (Docling) → normalize → chunk (par sections puis taille/overlap) → build → JSON. Exécution sur `mistral-doc.pdf` et vérification du fichier de chunks.
2. **Indexation** : configuration de l’index `pdf_chunks` (searchable, filterable, embedder Mistral) et chargement des 43 chunks via `run_pipeline.py --load`.
3. **Chat** : lecture de la doc Meilisearch (experimental-features, chats, workspace, stream completions). Implémentation de `setup_meilisearch_chat.py` et `ask_chat.py` en Python (pas de curl manuel).
4. **Dépannage** : 400 → upgrade Docker en v1.15.1 ; panic → activation de la master key et alignement `.env` ; réponse vide → debug SSE → détection de l’erreur “OpenAI” → ajout de `baseUrl` Mistral ; 401 → ajout des headers sur `/version` ; 403 → clarification clé master et `.strip()`.
5. **Validation** : quatre questions ciblées (architecture 47B/13B, benchmarks GSM8K/Humaneval, spécialisation des experts, benchmarks FR Table 4) ; toutes ont reçu des réponses correctes et ancrées dans le document.
6. **Transparence** : ajout de `search_chunks_for_query.py` pour montrer le **mode de search** (hybrid) et les **chunks** retournés pour une requête donnée (proxy des chunks envoyés au LLM).

---

## 5. Points positifs

- **Option A opérationnelle** : un seul appel API (chat completions) pour avoir une réponse RAG ; pas besoin de coder la boucle search → prompt → LLM soi-même.
- **Résultats sur un vrai PDF** : 4/4 questions validées (précision technique, tableaux, nuance sémantique, français) ; les tableaux et chiffres sont bien extraits et restitués.
- **Recherche hybride** : combinaison keyword + semantic (Mistral) ; les bons passages sont retrouvés (sections, tableaux, conclusion).
- **Stack cohérente** : un seul embedder (Mistral) pour l’index et un seul LLM (Mistral) pour le chat ; configuration centralisée (`.env`, `config/settings.py`).
- **Scripts reproductibles** : tout est faisable depuis le repo (setup, pipeline, ask, search_chunks_for_query) ; pas de dépendance à une UI Meilisearch.
- **Documentation des pièges** : version, master key, baseUrl, tools, 401/403 sont documentés dans le README et les commentaires ; un nouvel utilisateur peut éviter les mêmes erreurs.
- **Due diligence** : on a une preuve concrète que “Meilisearch + Mistral” peut servir de base à un RAG conversationnel sur un document technique complexe, avec une liste claire de limites et de prérequis.

---

## 6. Points négatifs

- **Feature expérimentale** : chat non stabilisé (panics, comportement par défaut trompeur) ; évolutions possibles de l’API ; à utiliser en connaissance de cause.
- **Pas de SDK chat** : pas de méthode dédiée dans le SDK Python ; tout passe par des appels HTTP (requests) et le parsing manuel du stream SSE.
- **Master key obligatoire pour le chat** : en local “sans auth” on ne peut pas utiliser le chat ; obligation de gérer une clé (≥ 16 caractères) et de la garder en sync entre Docker et `.env`.
- **Pas de sources dans la réponse** : les tools (dont _meiliSearchSources) sont désactivés ; on ne voit pas les chunks exacts envoyés au LLM dans la réponse du chat (seulement via le script proxy).
- **Un seul document testé** : un seul PDF (paper Mixtral) ; pas de variété de formats (rapports, slides, multi-langues) ni de volume.
- **Dépendance version Meilisearch** : besoin de v1.15.1+ ; toute infra ou doc doit le préciser.
- **Encodage affichage** : mojibake possible en sortie terminal ; cosmétique mais à noter.

---

## 7. Récapitulatif des fichiers `complex_pdf_test/`

| Dossier / Fichier | Type | Rôle en une phrase |
|-------------------|------|--------------------|
| **pipeline/** | | PDF → list de chunk dicts |
| pipeline/parse_pdf.py | Pipeline | PDF → markdown via Docling. |
| pipeline/normalize_elements.py | Pipeline | Normalisation du texte (regex). |
| pipeline/chunk_pdf.py | Pipeline | Découpage par sections puis par taille/overlap. |
| pipeline/build_documents.py | Pipeline | Construction des docs (chunks) au format cible. |
| pipeline/schemas.py | Données | Modèles RawElement, Chunk, chunk_to_meilisearch_doc. |
| **load/** | | Indexation Meilisearch |
| load/load_to_meilisearch.py | Indexation | Configure `pdf_chunks` (embedder Mistral) et charge les documents. |
| **chat/** | | Chat natif (Option A) |
| chat/setup_meilisearch_chat.py | Chat | Active chatCompletions, configure l’index pour le chat, crée le workspace Mistral (avec baseUrl). |
| chat/ask_chat.py | Chat | Envoie une question au chat, parse le stream SSE, affiche la réponse. |
| **audit/** | | Inspection |
| audit/search_chunks_for_query.py | Audit | Lance une recherche hybride (même logique que le chat) et affiche les chunks retournés. |
| **run_pipeline.py** | Orchestration | Enchaîne parse → normalize → chunk → build → JSON ; option `--load` pour Meilisearch. |
| **mistral-doc.pdf** | Donnée | PDF de test (paper Mixtral of Experts). |
| **mistral-doc.chunks.json** | Donnée | Sortie du pipeline (43 chunks). |
| **README.md** | Doc | Instructions et layout (pipeline, load, chat, audit). |
| **BILAN.md** | Doc | Ce document. |

---

## 8. Synthèse par rapport à la due diligence

- **Hybrid search** : validé sur un index de chunks réels (Mistral embedder) ; le chat s’appuie bien sur cette recherche.
- **RAG “natif”** : Option A testée de bout en bout ; réponses pertinentes et ancrées dans le document.
- **Feature expérimentale** : utilisable sous conditions (version, master key, baseUrl) ; les difficultés et contournements sont documentés.
- **Performance sur PDF complexe** : un paper avec tableaux et sections a été traité avec succès (chiffres, nuances, français).
- **Intégration Mistral** : embedding + chat ; une seule stack, configuration explicite (baseUrl) pour éviter les mauvais routages.

Ce bilan peut servir de **base factuelle** pour la partie “tests sur document réel” et “chat expérimental” du rapport de due diligence, en citant à la fois les résultats positifs et les réserves listées ci-dessus.
