// @ts-nocheck
import { ScrollViewStyleReset } from "expo-router/html";
import type { PropsWithChildren } from "react";

export default function Root({ children }: PropsWithChildren) {
  return (
    <html lang="en" style={{ height: "100%" }}>
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, shrink-to-fit=no"
        />
        {/*
          Disable body scrolling on web to make ScrollView components work correctly.
          If you want to enable scrolling, remove `ScrollViewStyleReset` and
          set `overflow: auto` on the body style below.
        */}
        <ScrollViewStyleReset />
        {/* ── Icon fonts ─────────────────────────────────────────────────────
            @expo/vector-icons injects its own font-face asynchronously via JS,
            so the very first render can show empty squares for all icons.
            Declaring the face here (before any React hydration) eliminates that
            flash.  The CDN URL matches the package version in package.json.     */}
        <style dangerouslySetInnerHTML={{ __html: `
          @font-face {
            font-family: 'Ionicons';
            src: url('https://cdn.jsdelivr.net/npm/@expo/vector-icons@15.1.1/build/vendor/react-native-vector-icons/Fonts/Ionicons.ttf') format('truetype');
            font-display: block;
          }
        ` }} />
        <style
          dangerouslySetInnerHTML={{
            __html: `
              body > div:first-child { position: fixed !important; top: 0; left: 0; right: 0; bottom: 0; }
              [role="tablist"] [role="tab"] * { overflow: visible !important; }
              [role="heading"], [role="heading"] * { overflow: visible !important; }
            `,
          }}
        />

        {/* ── Google Analytics 4 ──────────────────────────────────────────
            gtag.js is loaded async so it never blocks first paint.
            The config call fires a default page_view which GA4 needs to
            start session tracking; named events are sent from src/analytics. */}
        <script
          async
          src="https://www.googletagmanager.com/gtag/js?id=G-JDVMP7PKCV"
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              gtag('js', new Date());
              gtag('config', 'G-JDVMP7PKCV', { send_page_view: false });
            `,
          }}
        />

        {/* ── Cloudflare Web Analytics ────────────────────────────────────
            Lightweight beacon (< 1 KB), deferred, no cookies by default.
            Token is safe to expose in HTML — it only allows writing stats,
            not reading them. */}
        <script
          defer
          src="https://static.cloudflareinsights.com/beacon.min.js"
          data-cf-beacon='{"token": "4bf7b3812e52441981becae529ef1f18"}'
        />
      </head>
      <body
        style={{
          margin: 0,
          height: "100%",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {children}
      </body>
    </html>
  );
}
