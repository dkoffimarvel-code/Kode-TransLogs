# Kode-Agri — Customisation Odoo 19 « TMS Flotte »

Implémentation du *Cahier des charges – Logiciel de Gestion de Transport et de Flotte v3.3*
sous forme d'addons Odoo 19 (Community) qui étendent les applications standard
(Flotte, Achats, Stock, Comptabilité, Maintenance, RH, Congés, Notes de frais).

| Addon | Section du cahier des charges | Contenu |
|---|---|---|
| `tms_fleet` | §5 Parc auto, §7.1 facturation tournées, §4.3 centres de coût | Statut opérationnel, sites, GPS + géofencing (endpoint `/tms/gps/push`), tournées (planning, contraintes, facturation), carburant (détection d'anomalies), incidents, scoring conducteurs, documents/habilitations avec alertes, maintenance préventive, rapports programmés, centres de coût (plan analytique) |
| `tms_purchase` | §6 Achats & stock | Demandes d'achat (entête + lignes, validation) → commande fournisseur, centre de coût sur commandes/sorties de stock, référentiel fournisseurs évalué |
| `tms_asset` | §8 Immobilisations | Registre, plan d'amortissement linéaire/dégressif, écritures, cessions/rebut ; fiche créée automatiquement pour chaque véhicule |
| `tms_equipment` | §9 Maintenance des engins | Engins hors flotte, contrôles réglementaires + alertes, interventions et coûts par centre de coût |
| `tms_hr` | §10 RH, §11 Paie, §12 Notes de frais | Contrats/échéances, éléments variables, bulletins (simplifiés), notes de frais imputées par centre de coût ; congés = app Odoo standard |
| `tms_budget` | §13 Contrôle de gestion | Budgets par centre de coût / catégorie / période, budget vs réalisé, alertes, analyse des charges |

## Principe des centres de coût
Un centre de coût est un compte analytique du plan **« Centres de coût »**. Il est porté par le
véhicule, le conducteur/employé, le site, puis recopié par défaut sur chaque dossier (plein,
intervention, incident, tournée, commande, note de frais…) où il peut être modifié (§5.5, §13.2).
Chaque dossier valorisé génère une ligne analytique catégorisée (`tms.cost.mixin`), source du suivi budgétaire.

## Installation
1. Ajouter ce dépôt au `addons_path` d'Odoo 19.
2. Mettre à jour la liste des applications, installer `tms_budget`, `tms_hr`, `tms_equipment`,
   `tms_asset`, `tms_purchase` (installe `tms_fleet` en dépendance), ou seulement ceux voulus.
3. Groupes : *TMS / Conducteur*, *TMS / Exploitant*, *TMS / Responsable*.
4. Changer le paramètre système `tms_fleet.gps_token` (jeton des boîtiers GPS).

## Limites / hors périmètre de cette version
- La paie est une version simplifiée (taux de charges paramétrables `tms_hr.*_charge_rate`) ; pas de DSN ni de moteur de règles légales.
- Application mobile conducteur (§5.9) et optimisation automatique d'itinéraires (§5.3) non incluses ; le portail/PWA et un solveur sont à brancher (API Odoo).
- Code écrit sans instance Odoo 19 disponible : syntaxe Python/XML vérifiée, installation et tests fonctionnels à faire sur une base de recette.
