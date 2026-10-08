# AGI Project

TODO: Rest of the README

### Common Browser Issue: Insecure `IP:PORT` Access

Browsers often block features on HTTP `IP:PORT` connections because they are treated as non-secure origins.

#### Fix for Google Chrome

1. Open Chrome and navigate to:
```text
chrome://flags/#unsafely-treat-insecure-origin-as-secure
```

2. Enable **Insecure origins treated as secure**.
3. Add your target origin to the text box, e.g.:
```text
http://35.234.71.189:30080
```

*(Separate multiple origins with commas)*

4. Click **Relaunch** at the bottom right to restart Chrome.