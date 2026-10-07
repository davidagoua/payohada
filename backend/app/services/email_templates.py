"""Gabarits des emails transactionnels."""
import html


def _habillage(titre: str, intro: str, corps: str, pied: str = "") -> str:
    """Enveloppe commune aux emails PayOHADA (cohérente avec les bulletins)."""
    return f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333333; margin: 0; padding: 24px 12px; background: #f1f5f9;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0;">
    <div style="background-color: #16a34a; padding: 15px; text-align: center; color: #ffffff;">
      <h1 style="margin: 0; font-size: 20px; text-transform: uppercase;">payohada paie</h1>
    </div>
    <div style="padding: 24px;">
      <h2 style="margin: 0 0 12px; font-size: 17px; color: #0f172a;">{titre}</h2>
      <p style="margin: 0 0 16px;">{intro}</p>
      {corps}
      {pied}
    </div>
    <div style="padding: 14px 24px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 11px; color: #64748b; text-align: center;">
      Ce message a été généré automatiquement par payohada. Ne répondez pas à cet email.
    </div>
  </div>
</body>
</html>"""


def email_reinitialisation_mot_de_passe(
    prenom: str | None,
    nom: str | None,
    lien: str,
    minutes_validite: int,
) -> tuple[str, str]:
    """Email contenant le lien de réinitialisation.

    Retourne `(sujet, html)`. Les données d'état civil sont échappées : elles
    proviennent de la base et sont interpolées dans du HTML.
    """
    destinataire = html.escape(
        f"{prenom or ''} {nom or ''}".strip() or "bonjour"
    )
    lien_echappe = html.escape(lien, quote=True)

    corps = f"""
      <p style="margin: 0 0 20px; text-align: center;">
        <a href="{lien_echappe}"
           style="display: inline-block; padding: 12px 24px; background: #16a34a; color: #ffffff;
                  text-decoration: none; font-weight: bold; border-radius: 6px;">
          Choisir un nouveau mot de passe
        </a>
      </p>
      <p style="margin: 0 0 8px; font-size: 13px; color: #475569;">
        Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :
      </p>
      <p style="margin: 0 0 20px; font-size: 12px; word-break: break-all; color: #1d4ed8;">
        {lien_echappe}
      </p>
      <table style="width: 100%; border-collapse: collapse; margin: 0 0 16px; font-size: 13px;">
        <tr style="background: #f8fafc;">
          <td style="padding: 9px; border: 1px solid #cbd5e1; font-weight: bold;">Validité du lien</td>
          <td style="padding: 9px; border: 1px solid #cbd5e1;">{minutes_validite} minutes, une seule utilisation</td>
        </tr>
      </table>
    """

    pied = """
      <div style="padding: 12px; background: #fffbeb; border: 1px solid #fde68a; font-size: 12px; color: #92400e;">
        <strong>Vous n'êtes pas à l'origine de cette demande ?</strong><br>
        Ignorez simplement cet email : votre mot de passe actuel reste valable.
        Aucune donnée n'a été modifiée. Si vous recevez plusieurs messages de ce type,
        signalez-le à votre gestionnaire de paie.
      </div>
    """

    sujet = "Réinitialisation de votre mot de passe PayOHADA"
    intro = (
        f"Bonjour <strong>{destinataire}</strong>,<br><br>"
        "Vous avez demandé à réinitialiser le mot de passe de votre compte PayOHADA. "
        "Cliquez sur le bouton ci-dessous pour en choisir un nouveau."
    )
    return sujet, _habillage("Réinitialisation de mot de passe", intro, corps, pied)
