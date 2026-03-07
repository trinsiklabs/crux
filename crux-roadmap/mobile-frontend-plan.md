# mobile app strategy for Phoenix/Ash/Elixir stack

## what vibe coding platforms are using

the entire vibe coding ecosystem has converged on one stack for mobile: **React Native + Expo**.

- **Replit** uses React Native + Expo for its mobile app generation. their 2026 "Mobile Apps" feature transforms prompts into deployable iOS apps via Expo.
- **Bolt.new** supports Expo as their mobile framework. they added it specifically because web-only wasn't enough.
- **Natively** and **RapidNative** — two platforms purpose-built for vibe-coded mobile apps — both generate React Native + Expo code.
- **Lovable** and **v0** remain web-only. no mobile story.
- **Flutter** has fans but almost zero vibe coding platform support. the AI training data and tooling just isn't there yet compared to React Native.
- **Emergent** (YC-backed) uses AI agent teams but also targets React Native for mobile output.

for app store submission, **Expo EAS** (Expo Application Services) is the standard:

- `eas build` — cloud builds for iOS and Android without Xcode or Android Studio
- `eas submit` — automated submission to App Store and Google Play from the command line
- `eas submit --auto-submit` — automatically submits after build completes
- `eas update` — over-the-air updates without going through app store review
- GitHub Actions integration for CI/CD: build and submit on every merge to main

this is the pipeline every serious vibe coding platform uses to get apps into stores.

---

## the three realistic options for your stack

### Option 1: React Native + Expo (recommended)

**architecture:**
```
┌─────────────────────────┐     ┌──────────────────────────┐
│  React Native + Expo    │     │  Phoenix/Ash Backend     │
│  (TypeScript/JS)        │────▶│  REST API + GraphQL      │
│                         │     │  (Absinthe)              │
│  iOS + Android          │◀────│  Phoenix Channels (WS)   │
│  from one codebase      │     │  PostgreSQL              │
└─────────────────────────┘     └──────────────────────────┘
```

**why this is the move:**

- **AI tooling is best here.** Claude Code, Cursor, OpenCode — all generate high-quality React Native + Expo code. Expo even has an official MCP server so AI tools can interact with simulators and React Native DevTools directly. Callstack (core RN contributor) published official "React Native Best Practices for AI Agents" — the ecosystem is actively optimizing for vibe coding.
- **Absinthe (GraphQL) is the bridge.** your Phoenix/Ash backend already speaks GraphQL through Absinthe. React Native consumes GraphQL natively through Apollo Client or urql. this is a well-documented, battle-tested integration pattern.
- **Phoenix Channels for real-time.** React Native connects to Phoenix Channels via WebSocket for live updates, presence, pub/sub. the Elixir + React Native real-time architecture is documented and used in production.
- **Expo EAS handles the store nightmare.** one command to build. one command to submit. OTA updates bypass app review for non-native changes. this is the part that usually kills solo developers, and Expo has solved it.
- **largest ecosystem.** 13K+ npm packages compatible with Expo. every UI library, every payment SDK, every push notification service has a React Native integration.
- **Crux integration.** since you're building Crux as rails for AI coding tools, and those tools generate React Native better than anything else, your own product should use what the tools are best at generating.

**what you give up:**

- separate frontend codebase (TypeScript/JS, not Elixir)
- you need to learn React Native patterns (but AI tools handle most of this)
- two deployment pipelines (Expo EAS for mobile, your existing server for Phoenix)

**app store path:**
1. `eas build --platform all` — builds iOS + Android in Expo's cloud
2. `eas submit --platform all` — submits to both stores
3. first submission requires Apple Developer ($99/year) + Google Play ($25 one-time)
4. subsequent updates: OTA for JS changes, new build only for native changes

### Option 2: LiveView Native

**architecture:**
```
┌─────────────────────────┐
│  Phoenix LiveView       │
│  + LiveView Native      │
│  (all Elixir)           │
│                         │
│  Web + iOS + Android    │
│  from ONE codebase      │
│  (same .heex templates) │
└─────────────────────────┘
```

**the promise:**

LiveView Native (by DockYard) extends Phoenix LiveView to render native SwiftUI (iOS) and Jetpack Compose (Android) views. same Elixir codebase, same LiveView templates, same backend — the server renders UI diffs and pushes them to native clients over WebSocket.

this is the dream for a Phoenix/Ash shop. one language, one team, one codebase.

**the reality (as of March 2026):**

- **iOS:** stable client (SwiftUI). apps have been accepted into the App Store — DockYard confirmed Apple accepts LiveView Native apps as long as they follow guidelines.
- **Android:** Jetpack Compose client is still under development. last updated December 2025. not production-ready.
- **maturity:** v0.4.0-rc.1 released March 2025. the Elixir Forum consensus is that it's not ready for production use. DockYard themselves are still building the testing framework.
- **AI tooling:** essentially zero. no vibe coding platform generates LiveView Native code. Claude and Cursor have minimal training data for it. you'd be writing most of it by hand.
- **community:** small. compared to React Native's massive ecosystem, LiveView Native has a fraction of the libraries, examples, and Stack Overflow answers.
- **DockYard is accepting contracts** for LiveView Native development, which signals growing confidence, but also signals that most teams can't do it alone yet.

**verdict:** keep an eye on it. if Android reaches stability and AI training data catches up, this becomes the obvious choice for Elixir teams. but today, building production mobile apps on it is a gamble — especially solo.

### Option 3: Progressive Web App (PWA)

**architecture:**
```
┌─────────────────────────┐
│  Phoenix LiveView       │
│  (your existing web UI) │
│  + service worker       │
│  + web app manifest     │
│                         │
│  "install" on mobile    │
│  from the browser       │
└─────────────────────────┘
```

**when this makes sense:**

- your app doesn't need push notifications on iOS (Safari now supports them as of iOS 16.4, but the UX is rough)
- you don't need access to native APIs (Bluetooth, NFC, HealthKit, etc.)
- you want to skip the app stores entirely
- you want to ship fast and iterate before committing to native

**what you get:** your existing Phoenix LiveView web app, installable on the home screen, with offline support via service workers. zero additional codebase. zero app store fees.

**what you give up:** no app store presence (which matters for discovery), limited native API access, second-class citizen on iOS (Apple still throttles PWAs), no push notifications reliability.

**verdict:** great as a v1 / MVP mobile strategy while you build the real native app. ship the PWA now, build React Native + Expo when you're ready.

---

## recommendation

**short answer: React Native + Expo, with your Phoenix/Ash backend serving GraphQL (Absinthe) + Phoenix Channels.**

here's the phased plan:

### phase 1: foundation (weeks 1-2)

1. scaffold a new Expo project (`npx create-expo-app`)
2. set up Absinthe on your Phoenix backend if not already there (you likely already have REST — GraphQL through Absinthe is the cleaner mobile interface)
3. configure Apollo Client or urql in the Expo app to talk to your GraphQL endpoint
4. set up Phoenix Channels client for real-time features
5. get Expo Go running on your phone for hot-reload development
6. configure the Expo MCP server so Claude Code / Cursor can interact with your simulator directly

### phase 2: core app (weeks 3-6)

1. build your core screens using React Native + Expo components
2. use AI tools aggressively here — Claude Code generates solid React Native. lean into it.
3. use Expo's built-in libraries for camera, notifications, secure storage, etc.
4. integrate authentication (your Phoenix backend handles this, the app just stores tokens)
5. test on both iOS and Android via Expo Go and development builds

### phase 3: app store (weeks 7-8)

1. register Apple Developer account ($99/year) and Google Play Console ($25 one-time)
2. configure `eas.json` for production builds
3. set up app store metadata (screenshots, descriptions, privacy policy)
4. `eas build --platform all` for first production builds
5. `eas submit --platform all` to submit to both stores
6. set up CI/CD: GitHub Actions → EAS Build → EAS Submit on merge to `release` branch

### phase 4: iterate (ongoing)

1. use `eas update` for OTA JavaScript updates (skip app review for non-native changes)
2. monitor with Expo's built-in error reporting or Sentry
3. add native modules as needed via Expo's config plugins
4. when LiveView Native Android stabilizes + AI tooling catches up, evaluate migrating

### the LiveView Native hedge

don't abandon LiveView Native as a long-term play. the Elixir community is small but the technology is sound. the right move is:

- watch the GitHub repos (liveview-native/live_view_native, liveview-native/liveview-client-jetpack)
- try a small internal tool with LiveView Native to build familiarity
- when Android is stable + v1.0 ships, reassess. if AI tools start generating LiveView Native code well, that changes everything.

---

## cost summary

| item | cost |
|------|------|
| Apple Developer Program | $99/year |
| Google Play Console | $25 one-time |
| Expo EAS (free tier) | $0 (30 builds/month) |
| Expo EAS Production | $99/month (if you need more builds/priority) |
| **total to start** | **~$124** |

your Phoenix/Ash/PostgreSQL backend stays exactly as-is. you're just adding a new client that talks to it over GraphQL and WebSockets.
