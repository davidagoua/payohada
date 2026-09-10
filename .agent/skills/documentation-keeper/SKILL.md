---
name: documentation-keeper
description: Maintient automatiquement le fichier DOCUMENTATION.md à jour à chaque ajout, modification ou suppression de fonctionnalité dans le projet. À utiliser dès qu'une fonctionnalité, une API, une configuration ou une architecture est créée, modifiée ou supprimée.
---

# Documentation Keeper

Ce skill définit comment maintenir `DOCUMENTATION.md` (fichier unique à la racine du projet) synchronisé avec le code. Aucune fonctionnalité n'est considérée comme terminée tant que la documentation n'est pas à jour.

## When to use this skill

- Utilise ce skill **à chaque ajout de fonctionnalité** dans le projet.
- Utilise ce skill **à chaque modification** d'une fonctionnalité existante (comportement, paramètres, API).
- Utilise ce skill **à chaque suppression** d'une fonctionnalité, d'un endpoint ou d'une option.
- Utilise ce skill lors d'un **changement d'architecture**, de **configuration**, ou d'**ajout de variable d'environnement**.
- Utilise ce skill lors d'un **bugfix** qui change le comportement observable du code.
- Utile aussi quand l'agent termine une tâche et doit signaler ce qui a été documenté.

## How to use it

### 1. Règle fondamentale

> **Toute modification de code impactant une fonctionnalité DOIT être répercutée dans `DOCUMENTATION.md` dans la même itération.** Aucune exception.

Le fichier `DOCUMENTATION.md` vit **à la racine du projet**. C'est l'**unique** fichier de documentation autorisé. Il est interdit de créer `docs/`, un `README` détaillé, ou tout autre fichier de doc.

### 2. Structure imposée de `DOCUMENTATION.md`

Si le fichier n'existe pas, le créer avec cette structure exacte :

```markdown
# 📖 Documentation — <Nom du projet>

## 🧭 Vue d'ensemble
Description courte du projet (2-5 phrases). Stack technique, prérequis.

## 🚀 Démarrage rapide
Commandes d'installation, lancement, build.

## ⚙️ Configuration
Variables d'environnement, fichiers de config, options.

## 🧩 Fonctionnalités

### <Nom fonctionnalité 1>
...

### <Nom fonctionnalité 2>
...

## 🔌 API / Interfaces
Endpoints, signatures, formats d'entrée/sortie.

## 🏗️ Architecture
Organisation des dossiers, modules clés, flux principaux.

## 📅 Changelog

### [Unreleased]

#### Added
- ...

#### Changed
- ...

#### Fixed
- ...

#### Removed
- ...