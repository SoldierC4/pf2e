import { VehiclePF2e } from "@actor";
import { ErrorPF2e, fontAwesomeIcon, objectHasKey } from "@util";
import { TokenDocumentPF2e } from ".";

export class TokenConfigPF2e<TDocument extends TokenDocumentPF2e> extends TokenConfig<TDocument> {
    override get template(): string {
        return "systems/pf2e/templates/scene/token/sheet.html";
    }

    /** Get this token's dimensions were they linked to its actor's size */
    get dimensionsFromActorSize(): number {
        const actorSize = this.actor?.size ?? "med";
        return {
            tiny: 0.5,
            sm: 1,
            med: 1,
            lg: 2,
            huge: 3,
            grg: 4,
        }[actorSize];
    }

    /** Hide token-sight settings when rules-based vision is enabled */
    override activateListeners($html: JQuery): void {
        super.activateListeners($html);

        const html = $html[0]!;
        const linkToActorSize = html.querySelector<HTMLInputElement>('input[name="flags.pf2e.linkToActorSize"]');
        if (!linkToActorSize) throw ErrorPF2e("");

        linkToActorSize.addEventListener("change", (event) => {
            if (!(event.currentTarget instanceof HTMLInputElement)) {
                throw ErrorPF2e("Input element not found");
            }

            const sizeInputs = Array.from(
                event.currentTarget
                    .closest("fieldset")
                    ?.querySelectorAll<HTMLInputElement>("input[type=number]") ?? []
            );

            for (const input of sizeInputs) {
                input.disabled = linkToActorSize.checked;
            }

            const dimensionInputs = sizeInputs.filter((i) => ["width", "height"].includes(i.name));

            if (this.token.autoscale && linkToActorSize.checked) {
                if (this.actor instanceof VehiclePF2e) {
                    const { dimensions } = this.actor;
                    const dimensionValues: Record<string, number> = {
                        width: Math.max(Math.round(dimensions.width / 5), 1),
                        height: Math.max(Math.round(dimensions.length / 5), 1),
                    };
                    for (const input of dimensionInputs) {
                        input.value = dimensionValues[input.name].toString();
                    }
                } else {
                    for (const input of dimensionInputs) {
                        input.value = this.dimensionsFromActorSize.toString();
                    }
                }
            } else {
                const source = this.token._source;
                const nameToValue = {
                    width: source.width,
                    height: source.height,
                };
                for (const input of sizeInputs) {
                    if (objectHasKey(nameToValue, input.name)) {
                        input.value = nameToValue[input.name].toString();
                    }
                }
            }
        });

        this.#disableVisionInputs(html);
    }

    #disableVisionInputs(html: HTMLElement): void {
        const actorIsPCOrFamiliar = ["character", "familiar"].includes(this.actor?.type ?? "");
        const rulesBasedVision =
            actorIsPCOrFamiliar &&
            (this.token.rulesBasedVision ||
                (this.isPrototype && game.settings.get("pf2e", "automation.rulesBasedVision")));
        if (!rulesBasedVision) return;

        const sightInputNames = ["angle", "brightness", "range", "saturation", "visionMode"].map((n) => `sight.${n}`);
        const sightInputs = Array.from(
            html.querySelectorAll<HTMLInputElement | HTMLSelectElement>(
                sightInputNames.map((n) => `[name="${n}"]`).join(", ")
            )
        );

        const sightEnabledInput = html.querySelector<HTMLInputElement>('input[name="sight.enabled"]');
        if (!sightEnabledInput) throw ErrorPF2e("sight.enabled input not found");
        sightEnabledInput.addEventListener("change", () => {
            for (const input of sightInputs) {
                input.disabled = !sightEnabledInput.checked;
                if (input.type === "range") {
                    if (!sightEnabledInput.checked) {
                        input.closest(".form-group")?.classList.add("children-disabled");
                    } else {
                        input.closest(".form-group")?.classList.remove("children-disabled");
                    }
                } else if (input.name === "sight.color") {
                    const colorInput = input.parentElement?.querySelector<HTMLInputElement>("input[type=color]");
                    if (colorInput) colorInput.disabled = !sightEnabledInput.checked;
                }
            }
        });

        // Indicate that vision settings are managed by rules-based vision
        for (const input of sightInputs) {
            input.disabled = true;
            if (input.type === "range") {
                input.closest(".form-group")?.classList.add("children-disabled");
            }
        }

        // Disable detection-mode tab link
        html.querySelector<HTMLAnchorElement>("a.item[data-tab=detection]")?.classList.add("disabled");

        const managedBy = document.createElement("a");
        managedBy.className = "managed-by-rbv";
        managedBy.append(fontAwesomeIcon("robot"));
        managedBy.title = game.i18n
            .localize("PF2E.SETTINGS.Automation.RulesBasedVision.ManagedBy")
            .replace(/<\/?rbv>/g, "");
        for (const sightInput of sightInputs) {
            const anchor = managedBy.cloneNode(true);
            anchor.addEventListener("click", () => {
                const menu = game.settings.menus.get("pf2e.automation");
                if (!menu) throw ErrorPF2e("Automation Settings application not found");
                const app = new menu.type();
                app.render(true);
            });

            const label = sightInput.closest(".form-group")?.querySelector("label");
            label?.append(anchor);
        }
    }

    protected override async _updateObject(event: Event, formData: Record<string, unknown>) {
        if (formData["flags.pf2e.linkToActorSize"] === true) {
            if (this.actor instanceof VehiclePF2e) {
                const { dimensions } = this.actor;
                const width = Math.max(Math.round(dimensions.width / 5), 1);
                const length = Math.max(Math.round(dimensions.length / 5), 1);
                formData["width"] = width;
                formData["height"] = length;
            } else {
                formData["width"] = formData["height"] = this.dimensionsFromActorSize;
            }
        }
        return super._updateObject(event, formData);
    }
}
