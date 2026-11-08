# Pergola – förslag till ny sajt

Ombyggnad av https://www.lapergola.se/ (WordPress/Divi) som en statisk sida, på samma sätt som Hedens och Stage Door. Ingen byggkedja; öppna `index.html` eller publicera mappen med GitHub Pages.

## Samma grundtänk som originalet

Film i toppen och "Boka bord", söndagsmiddagen, menyn, om oss, boka bord, kontakt och öppettider. Bokningsknapparna använder samma WaiterAid-widget (bokabord.se) som originalet.

## Förbättringar (från Hedens och Stage Door)

- **Menyn som HTML i stället för PDF**: läsbar i mobilen, sökbar för Google, med flikar per del. Svenska och engelska som i PDF:en.
- **Öppetstatus i toppen** ("Vi öppnar kl. 16 i dag" / "Öppet i kväll från kl. 16"), stängda dagar via `data-closed`, och söndagsmenyn markeras på söndagar.
- **Fast rad i mobilen** med Boka bord och Ring.
- **Allergiinfo** synlig överst i menyn.
- **SEO**: schema.org `Restaurant`, Open Graph, canonical, sitemap, ikoner och manifest.
- **Snabbare**: AVIF-bilder i två storlekar, filmen laddas först när den spelas, bilden i toppen förladdas.
- **Tillgänglighet**: filmen går att pausa och spelas inte vid "minska rörelse", hoppa-till-menyn-länk, fokusmarkering, kontrast minst 4,5:1.
- **Borttaget**: det trasiga Instagramflödet (ersatt med länk), kontaktformuläret (ersatt med tel:/mailto:) och kvarglömt innehåll om körkortsutbildningar (Riskettan, AM) i sidfoten.

## Filer

| Fil | Vad den gör |
| --- | --- |
| `index.html` | Hela sajten, inklusive menyn |
| `style.css` | Stil. Färger och typsnitt står överst. |
| `oppet.js` | Öppettiderna och öppetstatusen (med självtest) |
| `bilder/` | Foton (AVIF + JPG), filmen och loggan |
| `original/` | Skrapat original: HTML, bilder, meny-PDF:er och `INNEHALL.md` |

## Att kontrollera med restaurangen

- **Stängningstid saknas** på originalsajten ("från kl. 16"). Sidan säger därför aldrig "stänger" eller "stängt nu".
- Postnummer saknas och har inte hittats på.
- Rättat från PDF:en: Margarita → Margherita, "fresh herbs & spruce" → "& grana", "Fonteroutoli" → Fonterutoli, och "chili" lagt till i den engelska texten till Pollo e Chili. "Pinot Grigio Puittano" står kvar som i menyn (stavningen osäker).
- Telefonnumret visas som 031-18 89 80 (originalet: 031-188980).
- Filmen `bilder/topvid.mp4` är originalets film utan de första 1,5 sekunderna (fasadskylten med loggan), utan ljud och omkodad: 2,4 MB i stället för 7,8 MB. Originalet ligger kvar i `original/bilder/`. Kommandot: `ffmpeg -ss 1.5 -i original/bilder/topvid.mp4 -an -vf "fps=30,format=yuv420p" -c:v libx264 -preset slow -crf 31 -movflags +faststart bilder/topvid.mp4`
- Adressen `https://joachimjohansson.github.io/lapergola/` i `og:`-taggar, canonical, sitemap och JSON-LD är antagen; byt när värdadressen är bestämd.
- Fotona kommer från lapergola.se; rättigheterna ligger hos restaurangen.
