
# Engineering Diagram Studio

A small plotting tool for engineering and antenna-pattern work.

Included:

- `diagram_studio.py` — Windows/macOS/Linux desktop version with Tkinter
- `app.py` — Streamlit web version
- `requirements.txt`

## Desktop version

Install Python 3.11+ and run:

```bash
pip install -r requirements.txt
python diagram_studio.py
```

The desktop version includes a full local Python plotting console.

Available console names:

```python
ax
fig
np
pd
curves
current
```

Example:

```python
x = np.linspace(0.5, 30, 500)
y = 20*np.log10(np.sin(np.deg2rad(5))/np.sin(np.deg2rad(x)))
ax.plot(x, y, label="cosecant")
ax.legend()
```

## Web version

Run locally:

```bash
streamlit run app.py
```

Then open the URL shown by Streamlit.

The web version intentionally uses a restricted plotting console.
Do not expose arbitrary Python `exec()` in a public web application.

## Put the project on GitHub

1. Create a new empty repository on GitHub, for example:
   `engineering-diagram-studio`
2. In the project folder open a terminal.
3. Run:

```bash
git init
git add .
git commit -m "Initial Engineering Diagram Studio"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/engineering-diagram-studio.git
git push -u origin main
```

Or simply use GitHub Desktop and publish the folder.

## Important: GitHub is not the web application host

GitHub stores the source code. GitHub Pages cannot run a normal Python/Tkinter app.

For a real public web app, deploy `app.py` to Streamlit Community Cloud.

## Deploy with Streamlit Community Cloud

1. Push this repository to GitHub.
2. Sign in to Streamlit Community Cloud with GitHub.
3. Choose **Create app** / **New app**.
4. Select the repository.
5. Branch: `main`
6. Main file path: `app.py`
7. Deploy.

Streamlit installs packages from `requirements.txt`.

After deployment you receive a public URL that other people can open in a browser.

## Antenna TXT format

The program recognizes the antenna data format beginning with columns such as:

- Elevation
- Azimuth
- Abs(Grlz)
- Abs(Cross)
- Abs(Copol)

It can create vertical and horizontal antenna cuts and normalize gain to 0 dB.

## Safety note

The desktop console intentionally executes Python locally and therefore should only run trusted commands.

The public web application does **not** expose arbitrary Python execution.
