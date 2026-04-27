# Feature Reference

This page documents every tab in detail — its purpose, every option, and
the kind of input/output you should expect.

---

## 🏗️ Project Architect

The flagship tab. Generates a complete project scaffold from a natural-
language description: source files, configuration, tests, README, and a
dependency manifest. Optionally runs `git init`.

### Inputs

- **Project Name** — used as the output folder name and woven into
  generated files (README, package metadata, etc.). Use a name like
  `MiniCache` or `http_craft`.
- **Description & Requirements** — the more specific the better. Mention
  the target users, key features, any specific patterns you want
  (async, OOP, functional, etc.). Don't over-describe — a good paragraph
  is usually enough.
- **Target Language / Framework** — pick from the dropdown. Affects
  conventions (folder structure, dependency-manifest format, idioms).

### Generation Options

- **Auto Git Init** — if `git` is on your `PATH`, runs `git init` and an
  initial commit on the generated project.
- **Generate README** — produces a project README with a summary, install
  instructions, and a usage outline.
- **Generate Dependencies** — produces the dependency manifest file
  appropriate for the language (`requirements.txt`, `package.json`,
  `Cargo.toml`, etc.).

### Advanced Settings

- **AI Temperature** (0.00–1.00) — lower values produce more
  deterministic, predictable output. Higher values produce more creative,
  varied output. For code, 0.3–0.5 is usually optimal. Defaults to 0.7.
- **Max Files** (3–30) — caps the size of the project the architect can
  design. Smaller numbers force the model to be focused; larger numbers
  let it sprawl.

### Right pane

- **Live Logs** — streaming feed of what the worker is doing
- **Project Tree** — folder/file hierarchy as it's designed
- **Code Preview** — each file's contents as they're generated; you can
  click any file in the tree to view it

### Lint button

After generation, the **🔧 Lint / Format** button runs the appropriate
formatter on the currently-previewed file:

| Extension | Tool |
|---|---|
| `.py` | `black` |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.json` | `prettier` |
| `.rs` | `rustfmt` |

If the tool isn't installed, the button is a no-op with a warning in the
log. We don't bundle formatters; we just defer to them when present.

---

## 📚 Library Generator

For when you want a focused single-purpose library — narrower in scope
than a full project. Three scope sizes (3–5, 5–8, or 8–12 files), with
optional tests, examples folder, and README.

The output is similar to **Project Architect** but smaller and tighter.
Use this for things like "a thread-safe LRU cache with TTL support" or
"an HTTP retry middleware" — single-concern code, not whole apps.

---

## 🧩 Code Refactor & Review

Five operating modes:

| Mode | What it does |
|---|---|
| **Refactor** | Cleaner, more idiomatic version of your code |
| **Security Review** | Markdown report on vulnerabilities and unsafe patterns |
| **Performance Optimization** | Markdown report on bottlenecks and improvements |
| **Explain Code** | Plain-language walkthrough of what the code does |
| **Modernize** | Updates to the latest stable syntax/idioms for the language |

### Style options

- **Concise** — minimum prose, get to the point
- **Balanced** — default; some explanation, mostly answer
- **Thorough** — explanations of reasoning, alternatives considered

### Behaviour-preservation toggle

The **Preserve original behavior** checkbox is on by default for the
**Refactor** and **Modernize** modes. When checked, the AI is instructed
not to change semantics — only to restructure or modernise. Turn it off
if you actually want behavioural improvements (e.g. fixing what looks
like an obvious bug while restructuring).

### Swap result → input button

After a result, the **↑ Use as Input** button moves the result back into
the input pane. This is great for iterative refinement — refactor once,
review the result, refactor again with a slightly different setting.

---

## 📖 Documentation Generator

Generates one of five kinds of documentation from source code:

| Kind | Output |
|---|---|
| **README** | A complete README.md with overview, install, usage, API, contributing |
| **API Reference** | Per-class/per-function reference, grouped logically |
| **Inline / Docstrings** | The same code, with idiomatic docstrings/JSDoc/comments added |
| **Tutorial / Walkthrough** | A step-by-step learning guide |
| **Changelog** | A draft changelog entry written as if the code is a new release |

### Output formats

- **Markdown** — default
- **reStructuredText** — for Sphinx/Python ecosystems
- **JSDoc** — for JavaScript/TypeScript inline mode
- **Sphinx** — reST with Sphinx-specific directives

### Audience targeting

The audience selector affects tone and assumed knowledge:

- **End Users** — minimal jargon, focus on what to do
- **Developers** — assumes programming literacy, focuses on integration
- **Contributors** — assumes familiarity with the codebase, focuses on
  internal architecture

---

## 🧪 Test Generator

Generates unit, integration, end-to-end, or property-based tests for
existing code. Frameworks are dynamically populated based on the chosen
language:

| Language | Frameworks offered |
|---|---|
| Python | pytest, unittest, hypothesis |
| JavaScript / TypeScript | Jest, Vitest, Mocha, Jasmine |
| Go | testing (stdlib), testify, ginkgo |
| Rust | cargo test, proptest |
| Java | JUnit 5, JUnit 4, TestNG |
| C# | xUnit, NUnit, MSTest |
| C++ | Google Test, Catch2, doctest |
| Ruby | RSpec, Minitest |
| ... and more |

### Coverage levels

- **Basic** — happy paths only, fast to write, fast to run
- **Thorough** — common paths plus edge cases (empty, null, boundaries,
  error handling) — recommended default
- **Exhaustive** — every branch, every condition; aims for full coverage

### Test style

- **AAA** (Arrange-Act-Assert) — explicit sections in each test
- **Given-When-Then** — BDD-flavoured naming
- **Minimal** — terse, one concern per test

### Options

- **Include fixtures/setup** — produces reusable setup code where helpful
- **Include mocks where helpful** — uses mocks/stubs for external
  dependencies; turn off for pure logic that doesn't need them
- **Include explanatory comments** — adds comments above non-obvious
  assertions

---

## 🎨 UI Component Generator

Generates frontend components in your framework of choice.

### Frameworks

- **React (TSX)** — TypeScript + React
- **React (JSX)** — JavaScript + React
- **Vue 3** — Composition API, single-file component
- **Svelte** — Svelte 5
- **HTML + CSS + JS** — fully self-contained, opens in any browser
- **SolidJS** — TypeScript

### Styling

Pick the styling approach that matches your codebase:

- Plain CSS, Tailwind CSS, styled-components, CSS Modules, or Inline styles

### Output mode

- **Single file** — one file, ready to copy into your project
- **Multi-file** — component + styles + tests + Storybook story (if
  enabled), written to disk in your output folder

### Options

- **Storybook story** (multi-file mode only) — adds a `.stories` file
- **Prop documentation** — documents all props in the language's
  idiomatic format
- **Accessibility best practices** — semantic HTML, ARIA attributes,
  keyboard navigation, focus management
- **Responsive** — works from mobile (320px) to desktop (1920px+)

### Browser preview

When the framework is **HTML + CSS + JS**, the **🔍 Preview in browser**
button writes the output to a temp file and opens it in your default
browser. This is the fastest way to iterate on a self-contained widget.

For other frameworks, the preview button is disabled because they need
a build step we don't bundle.

---

## 🗄️ Database Tools

Five operating modes:

| Mode | What it does |
|---|---|
| **Design Schema** | Natural-language description → DDL (CREATE TABLE, indexes, constraints) |
| **Optimize Query** | A slow query → diagnosis + optimised version + recommended indexes |
| **Generate Migration** | Description of a change → up/down migration scripts |
| **Generate Seed Data** | Description of test data → INSERT statements with realistic values |
| **Explain Query** | A query → human-readable explanation, useful for code review |

### SQL dialects

- PostgreSQL, MySQL, SQLite, SQL Server, Oracle

The output uses dialect-specific syntax (e.g. `SERIAL` vs `AUTO_INCREMENT`,
`JSONB` vs `JSON`, `RETURNING` clauses, etc.).

### ORM models (Schema mode only)

When you're designing a schema, the **ORM** dropdown lets you also get
matching ORM model code appended to the SQL output:

- SQLAlchemy 2.0 (Python)
- Prisma (Node.js / multiple languages)
- TypeORM (TypeScript)
- Django ORM (Python)
- Drizzle (TypeScript)
- None (SQL only)

### Options

The relevance of each option depends on the mode:

- **Include indexes** (schema, migration) — recommended indexes on FKs
  and frequent query columns
- **Include constraints** (schema, migration) — primary keys, foreign
  keys, unique, check
- **Include comments** (schema, seed) — `COMMENT ON` statements or
  explanatory comments

### Target Row Count (Seed mode only)

Distributed across all tables sensibly. 100 is a reasonable default for
local dev fixtures; bump to 10,000+ for performance testing data.

---

## 🔌 API Builder

Generates REST, GraphQL, or gRPC scaffolding.

### API Style

- **REST (JSON over HTTP)**
- **GraphQL**
- **gRPC**

### Frameworks

The framework dropdown updates based on style:

- **REST**: FastAPI, Flask, Express, NestJS, Spring Boot, ASP.NET Core,
  Gin, Echo, Axum, Actix-web, Rails, Laravel
- **GraphQL**: Strawberry, Graphene, Apollo Server, Mercurius,
  graphql-yoga, GraphQL Ruby, graphql-java, async-graphql, gqlgen
- **gRPC**: grpcio, grpc-node, grpc-go, tonic, grpc-java

### Authentication models

- None, JWT (Bearer), API Key (header), OAuth 2.0, Session-based

The auth setup is wired into the generated code — middleware, guards,
or interceptors as appropriate for the framework.

### Scope

- **Minimal** (3–4 files) — main entry point + 1-2 endpoints
- **Standard** (5–7 files) — proper structure with routes, services,
  models split out
- **Complete** (8–12 files) — full layered architecture, error handling,
  logging, validation

### Optional extras

- **Input validation** — Pydantic, Zod, class-validator, or whatever the
  framework idiomatically uses
- **OpenAPI/Swagger spec** (REST) or **schema.graphql** (GraphQL)
- **Integration tests** — covers at least the main endpoints
- **Dockerfile** — production-ready container definition

---

## 🐳 DevOps Templates

Nine template kinds:

| Kind | What it generates |
|---|---|
| **Dockerfile** | Single- or multi-stage Dockerfile |
| **docker-compose** | Multi-service compose.yml |
| **GitHub Actions Workflow** | `.github/workflows/ci.yml` with lint/test/build/deploy stages |
| **GitLab CI Pipeline** | `.gitlab-ci.yml` with similar staging |
| **Makefile** | Common targets: install, lint, test, build, run, clean, plus a help target |
| **Kubernetes Manifests** | Deployment + Service + Ingress |
| **Terraform Module** | HCL2 with provider, variables, resources, outputs |
| **Nginx Configuration** | Server block with reasonable defaults |
| **systemd Service** | Unit file with [Unit], [Service], [Install] |

### Target environment

- **Development** — fast iteration, debug logging, hot reload where
  applicable
- **Staging** — production-like with verbose logging
- **Production** — optimised, minimal, hardened

### Options

- **Multi-stage build** (Dockerfile) — typically yields 5–10× smaller
  final images
- **Healthcheck** — adds `HEALTHCHECK` directives, K8s probes, or
  compose healthcheck blocks as appropriate
- **Security hardening** — non-root user, read-only filesystem, dropped
  capabilities, security headers (Nginx), systemd hardening directives
- **Layer caching** — orders steps to maximise Docker cache hits or
  CI cache effectiveness
- **Comments** — toggle on/off for documented vs terse output

---

## 💬 AI Chat Console

Open-ended multi-turn conversation. Use this when no specialised tab
fits — exploring ideas, asking general questions, working through a
problem interactively.

### System Prompt

The optional system prompt at the top steers the AI's behaviour for the
entire conversation. Examples:

- *"You are a senior Rust mentor. When I show you code, focus on
  ownership and lifetimes."*
- *"Respond only in JSON."*
- *"Be terse. No preamble."*

Apply or Reset doesn't clear the conversation — it just adjusts the
system prompt for subsequent messages.

### Sending messages

Type in the input area and press **Ctrl+Enter** (or click **⮕ Send**).
The conversation history is sent with each request, so the AI sees the
full context every turn. This is also why the token counter at the top
right matters: long conversations get expensive.

### Counters

- **Messages** — total messages in the current conversation
- **Tokens** — approximate token count (rough estimate, ~4 characters per
  token); useful for keeping an eye on cost

### Toolbar

- **🗑 Clear Conversation** — wipes everything (with confirmation)
- **⬇ Export Chat** — saves the conversation to a Markdown file with a
  metadata header (date, provider, model)

---

## ⚙️ Settings

Covered in detail in **AI Providers Setup**. Quick summary:

- **General** — language, output directory, keyring status
- **Active Provider** — which provider every other tab uses
- **Per-provider blocks** — API key, validation, model selection for
  Architect and Coder slots

---

## 📘 Documentation

You're reading it.

---

## ℹ️ About

Octarinox lore, license info, GitHub link, and the credit reel.
