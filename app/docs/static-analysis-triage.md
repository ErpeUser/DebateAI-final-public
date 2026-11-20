# Static-Analysis-Triage

Die Baseline ist als **triagiert, aber nicht bereinigt** eingeordnet. Das
bedeutet: Jeder Befundtyp besitzt eine Zuständigkeit und eine konkrete nächste
Prüfung; kein Befund wird durch diese Einordnung zu einem grünen Qualitäts- oder
Release-Gate. Die exakten Dateien, Zeilen und Codes stehen im versionierten
[JSON-Bericht](static-analysis-baseline.json).

| Befund | Zuständigkeit | Einordnung | Nächster Schritt vor einem Gate |
| --- | --- | --- | --- |
| Knip `files`, `dependencies`, `devDependencies`, `unlisted`, `binaries`, `unresolved`, `cycles` | jeweiliges JS/TS-Paket | Im aktuellen Lauf sauber; der Scope bleibt durch die drei Paketkonfigurationen und die Ausschlüsse begrenzt. | Bei neuen Befunden nur geänderte Dateien prüfen und dynamische/Build-Einstiegspunkte belegen. |
| dependency-cruiser `no-circular` | Frontend/Docs/Release-Worker | Aktuell sauber; generierte Ausgaben und `node_modules` werden nicht verfolgt. | Neue Zyklen blockieren erst nach unabhängiger Prüfung der Resolver-/TypeScript-Abdeckung. |
| dependency-cruiser `no-<paket>-to-<paket>` | Paketbesitzer | Warnung für unerlaubte Importe zwischen getrennt deploybaren Paketen; derzeit kein Gate. | Nur bei einem konkreten Import einen API-Vertrag oder eine bewusst dokumentierte Ausnahme ergänzen. |
| deptry `DEP001` | Backend/Desktop | Import ist im gemessenen Requirements-Vertrag nicht direkt definiert. Das kann eine echte fehlende Laufzeitabhängigkeit, eine transitive Provider-Abhängigkeit oder ein internes Modul sein. | Import und Paketdefinition einzeln abgleichen; direkte Runtime-Abhängigkeit ergänzen oder eine begründete Modulzuordnung konfigurieren. |
| deptry `DEP002` | Backend/Desktop | Definierte Pakete werden im statischen Scan nicht direkt importiert. Optionale Provider, CLI-/Build-Einstiegspunkte und plattformspezifische Extras sind erwartete False Positives. | Paketverwendung im Runtime-/Build-Vertrag nachweisen, in einen optionalen Requirements-Scope verschieben oder entfernen. |
| deptry `DEP003` | Backend/Desktop | Import wird nur transitiv bereitgestellt und ist deshalb versions- und Installationsreihenfolge-abhängig. | Direkte Definition oder bewusst versionierter Plattformvertrag; kein pauschales Entfernen. |
| deptry `DEP004` | Backend/Desktop | Ein Test-/Entwicklungsimport fehlt in der Test-Definition. | Test-Requirements ergänzen oder den Testpfad als bewusst optional dokumentieren. |

Die Triage bleibt absichtlich konservativ: Der Baseline-Runner setzt keine
Ausnahmen automatisch und installiert keine Abhängigkeiten. Ein späteres Gate
muss zusätzlich einen Diff-Report liefern, der nur neue Befunde in geänderten
Dateien blockiert; die historische Baseline darf nicht als stillschweigende
Allowlist für neue Architekturdrift dienen.
