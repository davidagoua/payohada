/**
 * Liste + formulaire d'ajout/modification d'une rubrique RH d'un salarié
 * (entretiens, visites médicales, formations, absences, prêts…).
 *
 * Les huit onglets RH de la fiche salarié suivaient exactement le même schéma,
 * recopié à la main : ce composable le porte une seule fois.
 */
interface OptionsRessourceRh<F extends Record<string, unknown>> {
  salarieId: string | number
  /** Segment d'URL : `/salaries/{id}/{collection}` et `/salaries/{collection}/{itemId}`. */
  collection: string
  /** Valeurs d'un formulaire vierge ; ses clés sont celles reprises d'un élément édité. */
  formVide: () => F
  /** Champs date tronqués à `AAAA-MM-JJ` pour les `<input type="date">`. */
  champsDate?: (keyof F)[]
  messages: { cree: string, modifie: string, supprime: string, confirmation: string }
  /** Transforme le formulaire avant envoi (ex. téléversement d'un fichier). */
  preparer?: (form: F) => Promise<Record<string, unknown>> | Record<string, unknown>
  /** Appelé à chaque remise à zéro du formulaire. */
  surReinitialisation?: () => void
}

/** Élément RH renvoyé par l'API : seul `id` est garanti. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- forme propre à chaque rubrique
type ElementRh = { id: number } & Record<string, any>

export function useRessourceRh<F extends Record<string, unknown>>(options: OptionsRessourceRh<F>) {
  const { get, put, post, delete: apiDelete } = useApi()
  const toast = useToast()
  const { salarieId, collection, messages } = options

  const liste = ref<ElementRh[]>([])
  const showForm = ref(false)
  const editing = ref<ElementRh | null>(null)
  const form = ref<F>(options.formVide())

  const recharger = async () => {
    liste.value = (await get(`/salaries/${salarieId}/${collection}`)) || []
  }

  const reinitialiser = () => {
    showForm.value = false
    editing.value = null
    options.surReinitialisation?.()
    form.value = options.formVide()
  }

  const save = async () => {
    try {
      const payload = options.preparer ? await options.preparer(form.value) : { ...form.value }
      if (editing.value) {
        await put(`/salaries/${collection}/${editing.value.id}`, payload)
        toast.add({ title: 'Succès', description: messages.modifie, color: 'success' })
      } else {
        await post(`/salaries/${salarieId}/${collection}`, payload)
        toast.add({ title: 'Succès', description: messages.cree, color: 'success' })
      }
      reinitialiser()
      await recharger()
    } catch (e) {
      console.error(e)
    }
  }

  const edit = (item: ElementRh) => {
    editing.value = item
    const dates = new Set(options.champsDate || [])
    const valeurs: Record<string, unknown> = {}
    for (const champ of Object.keys(options.formVide())) {
      valeurs[champ] = dates.has(champ) ? (item[champ] ? item[champ].substring(0, 10) : '') : item[champ]
    }
    form.value = valeurs as F
    options.surReinitialisation?.()
    showForm.value = true
  }

  const remove = async (id: number) => {
    if (!confirm(messages.confirmation)) return
    try {
      await apiDelete(`/salaries/${collection}/${id}`)
      toast.add({ title: 'Succès', description: messages.supprime, color: 'success' })
      await recharger()
    } catch (e) {
      console.error(e)
    }
  }

  return { liste, showForm, editing, form, save, edit, remove, cancel: reinitialiser }
}
