# Spike — méthode de zoom animé (2026-06-08)

**Conclusion : utiliser `zoompan`.**

- `zoompan` PRÉSERVE le mouvement : PSNR 7,75 dB entre 1,0 s et 1,5 s du même clip (faible = très différent = mouvement + zoom bien présents). Le « gel » constaté auparavant venait du poster blanc / non-autoplay de l'aperçu (déjà corrigé), pas de zoompan.
- `crop:eval=frame` : indisponible dans ce build ffmpeg ("Option not found"). Non nécessaire.
- Ken Burns retenu : `zoompan=z='min(zoom+RATE,ZMAX)':d=1:x=centre:y=centre:s=WxH:fps=FPS`.
- Shake (position) : `crop` avec x/y oscillants (`sin`) sur fenêtre `between(t,T,T+0.3)` — supporté.
