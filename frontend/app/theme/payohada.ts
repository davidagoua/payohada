import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

/**
 * Thème PrimeVue de payohada.
 *
 * Il part du préréglage Aura et reprend la charte de `assets/css/main.css` :
 * - le vert de la marque est la couleur primaire (action, validation) ;
 * - le bleu encre #01173a porte la structure (en-têtes, encarts) ;
 * - les gris sont ceux de Carbon, et les rayons restent doux (8 px).
 * Voir `docs/CHARTE_GRAPHIQUE.md`.
 */
const green = {
  50: '#eefcf1',
  100: '#d9f7e0',
  200: '#b4eec2',
  300: '#83e29a',
  400: '#49d56b',
  500: '#28b44a',
  600: '#20973d',
  700: '#197b31',
  800: '#135e25',
  900: '#0d4019',
  950: '#08260f'
}

const navy = {
  50: '#f3f5f9',
  100: '#dfe6f1',
  200: '#c2d0e5',
  300: '#9fb2d1',
  400: '#748db4',
  500: '#536b93',
  600: '#3c5377',
  700: '#243c60',
  800: '#0f2548',
  900: '#01173a',
  950: '#030e21'
}

// Gris Carbon, alignés sur l'échelle « slate » redéfinie dans main.css.
const carbon = {
  0: '#ffffff',
  50: '#f4f4f4',
  100: '#e8e8e8',
  200: '#e0e0e0',
  300: '#c6c6c6',
  400: '#a8a8a8',
  500: '#6f6f6f',
  600: '#525252',
  700: '#393939',
  800: '#262626',
  900: '#161616',
  950: '#161616'
}

export default definePreset(Aura, {
  primitive: {
    green,
    navy,
    borderRadius: {
      none: '0',
      xs: '4px',
      sm: '6px',
      md: '8px',
      lg: '10px',
      xl: '12px'
    }
  },
  semantic: {
    primary: {
      50: '{green.50}',
      100: '{green.100}',
      200: '{green.200}',
      300: '{green.300}',
      400: '{green.400}',
      500: '{green.500}',
      600: '{green.600}',
      700: '{green.700}',
      800: '{green.800}',
      900: '{green.900}',
      950: '{green.950}'
    },
    // Contour de focus Carbon : 2 px plein, dans la couleur d'action.
    focusRing: {
      width: '2px',
      style: 'solid',
      color: '{primary.600}',
      offset: '-2px',
      shadow: 'none'
    },
    formField: {
      paddingX: '1rem',
      paddingY: '0.625rem',
      borderRadius: '{border.radius.md}',
      focusRing: {
        width: '2px',
        style: 'solid',
        color: '{primary.600}',
        offset: '-2px',
        shadow: 'none'
      },
      transitionDuration: '70ms'
    },
    colorScheme: {
      light: {
        surface: carbon,
        primary: {
          color: '{primary.600}',
          contrastColor: '#ffffff',
          hoverColor: '{primary.700}',
          activeColor: '{primary.800}'
        },
        highlight: {
          background: '{navy.50}',
          focusBackground: '{navy.100}',
          color: '{navy.900}',
          focusColor: '{navy.900}'
        },
        mask: {
          background: 'rgba(3, 14, 33, 0.55)',
          color: '{surface.200}'
        },
        // Champ Carbon : fond gris clair, filet inférieur seulement.
        formField: {
          background: '{surface.50}',
          disabledBackground: '{surface.50}',
          filledBackground: '{surface.50}',
          filledHoverBackground: '{surface.100}',
          filledFocusBackground: '{surface.50}',
          // Le filet inférieur seul des champs est posé dans main.css ;
          // les cases à cocher et boutons radio gardent un contour complet.
          borderColor: '{surface.500}',
          hoverBorderColor: '{surface.700}',
          focusBorderColor: '{primary.600}',
          invalidBorderColor: '#da1e28',
          color: '{surface.900}',
          disabledColor: '{surface.400}',
          placeholderColor: '{surface.400}',
          invalidPlaceholderColor: '#da1e28',
          floatLabelColor: '{surface.600}',
          floatLabelFocusColor: '{primary.600}',
          floatLabelActiveColor: '{surface.600}',
          floatLabelInvalidColor: '#da1e28',
          iconColor: '{surface.500}',
          shadow: 'none'
        },
        text: {
          color: '{surface.900}',
          hoverColor: '{surface.900}',
          mutedColor: '{surface.600}',
          hoverMutedColor: '{surface.700}'
        },
        content: {
          background: '#ffffff',
          hoverBackground: '{surface.100}',
          borderColor: '{surface.200}',
          color: '{surface.900}',
          hoverColor: '{surface.900}'
        },
        overlay: {
          select: {
            background: '#ffffff',
            borderColor: '{surface.200}',
            color: '{surface.900}'
          },
          popover: {
            background: '#ffffff',
            borderColor: '{surface.200}',
            color: '{surface.900}'
          },
          modal: {
            background: '#ffffff',
            borderColor: '{surface.200}',
            color: '{surface.900}'
          }
        },
        navigation: {
          item: {
            focusBackground: '{surface.100}',
            activeBackground: '{surface.100}',
            color: '{surface.900}',
            focusColor: '{surface.900}',
            activeColor: '{surface.900}',
            icon: {
              color: '{surface.600}',
              focusColor: '{navy.900}',
              activeColor: '{navy.900}'
            }
          }
        }
      }
    }
  },
  components: {
    // Titres de modale à l'encre navy, comme les titres de page.
    dialog: {
      title: {
        fontSize: '1rem',
        fontWeight: '600'
      },
      colorScheme: {
        light: {
          root: {
            borderRadius: '{border.radius.xl}'
          }
        }
      }
    },
    button: {
      root: {
        borderRadius: '{border.radius.lg}',
        label: {
          fontWeight: '600'
        }
      }
    },
    // Notifications Carbon : fond opaque, sans flou ni transparence.
    toast: {
      root: {
        borderRadius: '{border.radius.lg}',
        blur: '0'
      },
      colorScheme: {
        light: {
          info: { background: '{navy.50}', borderColor: '{navy.200}', color: '{navy.900}', detailColor: '{surface.700}' },
          success: { background: '{green.50}', borderColor: '{green.200}', color: '{green.800}', detailColor: '{surface.700}' },
          warn: { background: '#fdf6dd', borderColor: '#f1c21b', color: '#8e6a00', detailColor: '{surface.700}' },
          error: { background: '#fff1f1', borderColor: '#ffb3b8', color: '#a2191f', detailColor: '{surface.700}' }
        }
      }
    },
    datatable: {
      colorScheme: {
        light: {
          headerCell: {
            background: '{navy.900}',
            color: '#ffffff',
            borderColor: '{primary.600}'
          }
        }
      }
    }
  }
})
