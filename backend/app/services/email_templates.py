"""Gabarits des emails transactionnels."""
import html

from app.config import settings


def lien_connexion() -> str:
    """URL de la page de connexion, reprise dans les emails d'accès."""
    base = (settings.FRONTEND_BASE_URL or "").rstrip("/")
    return f"{base}/login"


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


def email_acces_cree(
    prenom: str | None,
    nom: str | None,
    email_compte: str,
    mot_de_passe: str,
    nom_dossier: str | None,
    lien_connexion: str,
    changement_requis: bool = True,
    espace_libelle: str = "Espace Entreprise",
    espace_usage: str = (
        "saisir les variables de paie du mois et de consulter les bulletins "
        "de l'entreprise"
    ),
) -> tuple[str, str]:
    """Email d'identifiants remis au client ou au salarié, à la création ou au renvoi.

    Sans cet email, le mot de passe provisoire n'existerait que dans une
    notification à l'écran, que personne ne transmettait au titulaire du
    compte. Retourne `(sujet, html)`.

    `espace_libelle` et `espace_usage` adaptent le message à la plateforme :
    l'entreprise cliente et le salarié ne partagent ni les mêmes écrans ni les
    mêmes droits. Le sujet n'est pas échappé (ce n'est pas du HTML) ; tout ce
    qui entre dans le corps l'est, car le nom du dossier vient de la base.
    """
    destinataire = f"{prenom or ''} {nom or ''}".strip() or "bonjour"
    dossier_libelle = (nom_dossier or "votre entreprise").strip()
    lien_echappe = html.escape(lien_connexion, quote=True)

    corps = f"""
      <table style="width: 100%; border-collapse: collapse; margin: 0 0 18px; font-size: 13px;">
        <tr style="background: #f8fafc;">
          <td style="padding: 9px; border: 1px solid #cbd5e1; font-weight: bold;">Espace</td>
          <td style="padding: 9px; border: 1px solid #cbd5e1;">{html.escape(espace_libelle)} — {html.escape(dossier_libelle)}</td>
        </tr>
        <tr>
          <td style="padding: 9px; border: 1px solid #cbd5e1; font-weight: bold;">Identifiant</td>
          <td style="padding: 9px; border: 1px solid #cbd5e1;">{html.escape(email_compte)}</td>
        </tr>
        <tr style="background: #f8fafc;">
          <td style="padding: 9px; border: 1px solid #cbd5e1; font-weight: bold;">
            Mot de passe {"provisoire" if changement_requis else ""}
          </td>
          <td style="padding: 9px; border: 1px solid #cbd5e1; font-family: monospace;
                     font-size: 14px;">{html.escape(mot_de_passe)}</td>
        </tr>
      </table>
      <p style="margin: 0 0 20px; text-align: center;">
        <a href="{lien_echappe}"
           style="display: inline-block; padding: 12px 24px; background: #16a34a; color: #ffffff;
                  text-decoration: none; font-weight: bold; border-radius: 6px;">
          Me connecter
        </a>
      </p>
      <p style="margin: 0 0 8px; font-size: 13px; color: #475569;">
        Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :
      </p>
      <p style="margin: 0 0 20px; font-size: 12px; word-break: break-all; color: #1d4ed8;">
        {lien_echappe}
      </p>
    """

    if changement_requis:
        pied = """
      <div style="padding: 12px; background: #fffbeb; border: 1px solid #fde68a; font-size: 12px; color: #92400e;">
        <strong>Ce mot de passe est provisoire.</strong><br>
        À votre première connexion, remplacez-le par un mot de passe que vous seul
        connaissez. Personne, ni votre cabinet comptable ni l'équipe payohada, n'a
        besoin de le connaître.
      </div>
    """
    else:
        pied = """
      <div style="padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; font-size: 12px; color: #475569;">
        Conservez ce mot de passe. Vous pouvez le changer à tout moment depuis
        l'espace Entreprise, rubrique « Mon profil ».
      </div>
    """

    sujet = f"Vos identifiants payohada — {dossier_libelle}"
    intro = (
        f"Bonjour <strong>{html.escape(destinataire)}</strong>,<br><br>"
        f"Un accès à l'{html.escape(espace_libelle)} de "
        f"<strong>{html.escape(dossier_libelle)}</strong> vient d'être créé pour "
        f"vous. Il permet de {html.escape(espace_usage)}."
    )
    return sujet, _habillage("Votre accès à payohada", intro, corps, pied)
