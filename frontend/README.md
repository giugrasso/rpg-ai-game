# Node.js Installation Guide

## Prerequisites

- Operating System: Windows, macOS, or Linux

## Linux

### Steps

1. **Download Node.js**
    - Visit [nodejs.org](https://nodejs.org/)
    - Choose the LTS version for stability.

2. **Install Node.js**
    - Run the downloaded installer.
    - Follow the installation prompts.
    - Accept the license agreement and default settings.

3. **Verify Installation**
    - Open a terminal or command prompt.
    - Run:
      ```sh
      node -v
      npm -v
      ```
    - You should see version numbers for both Node.js and npm.

## Windows

[Doc Windows](https://learn.microsoft.com/fr-fr/windows/dev-environment/javascript/nodejs-on-windows)

**Winget**

- Install via Winget

  ```powershell
  winget install OpenJS.NodeJS.LTS
  ```

  **Si erreur**

  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser Unrestricted
  ```

- Test

  ```powershell
  node -v
  npm -v
  ```

  > Si ça ne fonctionne pas, fermer le terminal et rouvrir

## Additional Resources

- [Node.js Documentation](https://nodejs.org/en/docs/)
- [npm Documentation](https://docs.npmjs.com/)
