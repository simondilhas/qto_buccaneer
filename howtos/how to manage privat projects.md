# How and why to manage private and public projects

## Why?
- I want to work parallely in the same repo on a project that should not be published on github.

## How?
1. add __private/ to .gitignore (if you clone it's already so)
2. publish the my_projact__privat folder to your own privat repo (you will se it grey in the tree view in vscode)
3. have your main git normaly and your private one side by side

### Workflow
Creating a Private Repo for a __private Folder

Navigate into the __private folder:

```bash
cd path/to/your_folder__private
```

Initialize a Git repository:
```bash
git init
```

Set the remote to the corresponding private GitHub repository:

```bash
git remote add origin https://github.com/<your_username>/<private_repo_name>.git
```

Rename the default branch to main:

```bash
git branch -m main
```

Force push to the private repository (only required when GitHub created a README during repo initialization):

```bash
git push --force -u origin main
```

Syncing Changes

To push updates to the private repo:

```bash
cd path/to/your_folder__private
git add .
git commit -m "Update private folder"
git gpushp
```

Setting up Git Alias (One-time setup)

To make pushing private folders easier, add this alias:

```bash
git config --global alias.gpushp "push --force -u origin main"
```

Then use git gpushp to quickly push private folders.

**Always make sure you are operating inside the correct folder (__private) when pushing private changes.**

```bash
git gpushp
```