// Auto-generated from docs/guides/guide-klassrumskartan-kom-igang.md
// Do not edit manually. Re-generate with: pdm run generate-planner-help

export const plannerHelpTitles: Record<string, string> = {
  planner_overview: "Översikt: klass och klassrum",
  planner_seating: "Sittplatser",
  planner_grouping: "Grupper",
  planner_rules: "Regler och sammanfattning",
};

export const plannerHelpSections: Record<string, string> = {
  planner_overview: `<p>Klassrumskartan hjälper dig att skapa sittplaceringar och grupper utan att behöva rita för hand, klistra lappar eller klura ut i huvudet vem som satt var förra gången. Programmet håller reda på historiken, ser till att det blir rättvist över tid, och kan ta hänsyn till de observationer du har gjort om hur dina elever fungerar bäst.</p>
<p>Den här guiden tar dig genom de fyra grundstegen: <strong>klass</strong> -- <strong>klassrum</strong> -- <strong>sittschema / grupper</strong> -- <strong>regler</strong>.</p>
<h3>Steg 1 -- Skapa din första klass</h3>
<p>Det första du behöver är en klasslista.</p>
<ol><li>Gå till <strong>Översikt</strong> (startsidan i appen).</li><li>Klicka <strong>skapa ny klasslista</strong>.</li><li>Klistra in eller dra in din klasslista. Det enklaste är att kopiera listan rakt av från <strong>Skola24</strong>. Alla format fungerar -- du kan kopiera från en tabell, en PDF, eller en textfil -- men Skola24 är det säkraste alternativet och det du förmodligen redan har öppet när du rapporterar närvaro.</li><li>Förhandsgranska att namnen stämmer.</li><li>Spara.</li></ol>
<h3>Steg 2 -- Skapa ditt första klassrum</h3>
<p>Nu behöver du ett klassrum att placera eleverna i.</p>
<ol><li>Gå till <strong>Översikt</strong>.</li><li>Klicka <strong>skapa nytt klassrum</strong> och ge det ett namn (t.ex. "B214").</li></ol>
<h4>Verktyg</h4>
<p>När du skapar ditt klassrum har du en verktygsmeny till vänster:</p>
<ul><li><strong>Placera plats</strong> -- sätter ut stolar. Det här är det enda du <em>måste</em> använda.</li><li><strong>Möbler</strong> -- kateder, whiteboard, bord, bänk, fönster, dörr. Valfritt, men gör det lättare att se hur rummet är möblerat.</li><li><strong>Sudda</strong> -- ta bort enstaka objekt genom att klicka på dem.</li><li><strong>Rensa</strong> -- töm hela klassrummet.</li></ul>
<p>Grundprincipen: välj ett verktyg, klicka i rutnätet för att placera. Vill du ångra? Klicka på samma ruta igen så försvinner objektet.</p>
<h4>Varför möbler spelar roll</h4>
<p>Du <em>behöver</em> inga möbler -- bara stolar räcker. Men om du lägger till en <strong>kateder</strong> och en <strong>whiteboard</strong> så vet programmet ungefär var du som lärare brukar stå. Det använder den informationen när du låter programmet göra smarta placeringar (till exempel "nära läraren").</p>
<p>Utan kateder och whiteboard antar programmet att du står högst upp i mitten av klassrummet. Oftast stämmer det hyfsat, men har du en annorlunda möblering så får du bättre resultat om du lägger till dem.</p>`,
  planner_seating: `<h3>Steg 3 -- Skapa ditt första sittschema</h3>
<ol><li>Gå till <strong>Sittplatser</strong> i toppmenyn.</li><li>Välj ditt klassrum i verktygsfältet.</li></ol>
<h4>Placera elever</h4>
<p>Du har flera sätt att placera eleverna:</p>
<ul><li><strong>Slumpa</strong> -- slumpar ut alla elever på tillgängliga platser.</li><li><strong>Använd historik</strong> (toggle) -- programmet undviker att elever hamnar på samma plats som senast. Ju mer historik du har, desto rättvisare blir det.</li><li><strong>Smart</strong> (toggle) -- tar hänsyn till dina regler (se steg 5).</li><li><strong>Manuellt</strong> -- dra elever från elevlistan till en stol, eller flytta dem mellan platser.</li></ul>
<p>Du kan kombinera: slumpa först, justera manuellt sedan.</p>
<h4>Utkast och historik</h4>
<p>Varje sittschema du arbetar med är ett <strong>utkast</strong>. Du kan ändra fritt -- slumpa om, flytta, börja om -- utan att något "räknas".</p>
<p><strong>Först när du exporterar</strong> sparas din placering i historiken. Det är den historiken som programmet använder när du klickar i "Använd historik" nästa gång.</p>
<p>Så tankesättet är: <em>prova på, och när du är nöjd -- exportera.</em></p>
<p>Vill du börja på en helt ny placering? Klicka <strong>Nytt sittschema</strong> så får du ett nytt tomt utkast. Ditt gamla utkast finns kvar under <strong>Historik</strong> i menyn så du alltid kan gå tillbaka och titta.</p>
<h4>Export</h4>
<p>När du är nöjd, klicka <strong>Exportera</strong>:</p>
<ul><li><strong>Affisch A3 liggande</strong> (förvalt) -- bra att sätta upp i klassrummet</li><li><strong>Affisch A4 liggande</strong> -- om du föredrar mindre format</li><li><strong>Excel</strong> -- om du vill ha det digitalt eller bearbeta vidare</li></ul>`,
  planner_grouping: `<h3>Steg 4 -- Skapa din första gruppering</h3>
<ol><li>Gå till <strong>Grupper</strong> i toppmenyn.</li><li>Välj antal grupper med <strong>+</strong> och <strong>-</strong>.</li><li>Klicka <strong>Slumpa</strong> -- eller dra elever manuellt till grupperna.</li></ol>
<p>Grupper fungerar på samma sätt som sittplatser, men du behöver inget klassrum. Det gör det användbart även för ämneslärare som bara vill skapa grupper för sitt ämne utan att blanda in någon klassrumsplacering.</p>
<p>Export: <strong>Excel</strong> (förvalt) eller <strong>PDF A4 stående</strong>.</p>`,
  planner_rules: `<h3>Steg 5 -- Regler (smarta placeringar)</h3>
<p>Regler är observationer du sparar om hur dina elever fungerar bäst. När du sedan slumpar med <strong>Smart</strong> påslaget tar programmet hänsyn till dem.</p>
<p>Gå till <strong>Regler</strong> i toppmenyn. Där finns tre regeltyper:</p>
<table><thead><tr><th>Regel</th><th>Vad den gör</th><th>Exempel</th></tr></thead><tbody><tr><td><strong>Nära läraren</strong></td><td>Eleven placeras alltid i första raden</td><td>Elev som behöver extra stöd</td></tr><tr><td><strong>Håll isär</strong></td><td>Minst en rad eller kolumn mellan eleverna</td><td>Två som stör varandra</td></tr><tr><td><strong>Håll nära</strong></td><td>Placeras bredvid eller en rad ifrån</td><td>Kompis som trygghet, eller ett par</td></tr></tbody></table>
<p>Regler gäller för hela klassen -- inte bara för ett enskilt utkast. De aktiveras genom <strong>Smart</strong>-toggeln i sittplatser eller grupper.</p>
<h4>Färre regler = bättre resultat</h4>
<p>Programmet gör sitt bästa för att uppfylla alla regler, men med för många regler måste det kompromissa. Då kan resultatet bli sämre än om du hade haft färre, tydligare regler.</p>
<p>Mitt tips: börja med <em>noll</em> regler. Använd bara Slumpa + historik. Lägg till en regel först när du märker att du manuellt flyttar samma elev varje gång -- då har du hittat en regel värd att spara.</p>
<h3>Sammanfattning</h3>
<ol><li><strong>Klass</strong> -- importera från Skola24.</li><li><strong>Klassrum</strong> -- lägg ut stolar (och gärna kateder + whiteboard).</li><li><strong>Sittschema / Grupper</strong> -- slumpa, justera, exportera.</li><li><strong>Regler</strong> -- lägg till vid behov, men håll dem få.</li></ol>
<p>Det går inte att göra fel. Du kan alltid börja om, slumpa igen eller ta bort ett utkast. Prova dig fram -- det är precis så det är tänkt.</p>`,
};
