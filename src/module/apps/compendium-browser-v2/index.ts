import { Progress } from "./progress";
import { PhysicalItemPF2e } from "@item/physical";
import { KitPF2e } from "@item/kit";
import { ErrorPF2e, objectHasKey } from "@util";
import { ActorPF2e, FamiliarPF2e } from "@actor";
import { LocalizePF2e } from "@system/localize";
import {
    CompendiumBrowserActionTab,
    CompendiumBrowserBestiaryTab,
    CompendiumBrowserEquipmentTab,
    CompendiumBrowserFeatTab,
    CompendiumBrowserHazardTab,
    CompendiumBrowserSpellTab,
} from "./tabs/index";
import { TabData, PackInfo, TabName, TabType, SortDirection } from "./data";
import { CheckBoxdata, RangesData } from "./tabs/data";

class PackLoader {
    loadedPacks: {
        Actor: Record<string, { pack: CompendiumCollection; index: CompendiumIndex } | undefined>;
        Item: Record<string, { pack: CompendiumCollection; index: CompendiumIndex } | undefined>;
    } = { Actor: {}, Item: {} };

    async *loadPacks(documentType: "Actor" | "Item", packs: string[], indexFields: string[]) {
        this.loadedPacks[documentType] ??= {};
        const translations = LocalizePF2e.translations.PF2E.CompendiumBrowser.ProgressBar;

        const progress = new Progress({ steps: packs.length });
        for await (const packId of packs) {
            let data = this.loadedPacks[documentType][packId];
            if (!data) {
                const pack = game.packs.get(packId);
                if (!pack) {
                    progress.advance("");
                    continue;
                }
                progress.advance(game.i18n.format(translations.LoadingPack, { pack: pack.metadata.label }));
                if (pack.documentName === documentType) {
                    const index = await pack.getIndex({ fields: indexFields });
                    const firstResult = index.contents[0] ?? {};
                    // Every result should have the 'data' property otherwise the indexFields were wrong for that pack
                    if (firstResult.data) {
                        data = { pack, index };
                        this.loadedPacks[documentType][packId] = data;
                    } else {
                        continue;
                    }
                } else {
                    continue;
                }
            } else {
                const { pack } = data;
                progress.advance(game.i18n.format(translations.LoadingPack, { pack: pack?.metadata.label ?? "" }));
            }

            yield data;
        }
        progress.close(translations.LoadingComplete);
    }
}

export class CompendiumBrowserV2 extends Application {
    settings!: Omit<TabData<Record<string, PackInfo | undefined>>, "settings">;
    dataTabsList = ["action", "bestiary", "equipment", "feat", "hazard", "spell"] as const;
    tabs: Record<Exclude<TabName, "settings">, TabType>;
    packLoader = new PackLoader();
    activeTab!: TabName;
    navigationTab!: Tabs;

    /** Is the user currently dragging a document from the browser? */
    private userIsDragging = false;

    /** An initial filter to be applied upon loading a tab */
    private initialFilter: string[] = [];
    private initialMaxLevel = 0;

    constructor(options = {}) {
        super(options);

        this.tabs = {
            action: new CompendiumBrowserActionTab(this),
            bestiary: new CompendiumBrowserBestiaryTab(this),
            equipment: new CompendiumBrowserEquipmentTab(this),
            feat: new CompendiumBrowserFeatTab(this),
            hazard: new CompendiumBrowserHazardTab(this),
            spell: new CompendiumBrowserSpellTab(this),
        };
        this.loadSettings();
        this.initCompendiumList();
        this.injectActorDirectory();
        this.hookTab();
    }

    override get title() {
        return game.i18n.localize("PF2E.CompendiumBrowser.Title");
    }

    static override get defaultOptions() {
        return mergeObject(super.defaultOptions, {
            id: "compendium-browser-v2",
            classes: [],
            template: "systems/pf2e/templates/compendium-browser/compendium-browser.html",
            width: 800,
            height: 700,
            resizable: true,
            dragDrop: [{ dragSelector: "ul.item-list > li.item" }],
            tabs: [
                {
                    navSelector: "nav",
                    contentSelector: "section.content",
                    initial: "landing-page",
                },
            ],
            scrollY: [".control-area", ".item-list"],
        });
    }

    override async _render(force?: boolean, options?: RenderOptions) {
        await super._render(force, options);
        this.activateResultListeners();
    }

    /** Reset initial filtering */
    override async close(options?: { force?: boolean }): Promise<void> {
        this.initialFilter = [];
        this.initialMaxLevel = 0;
        await super.close(options);
    }

    private initCompendiumList() {
        const settings: Omit<TabData<Record<string, PackInfo | undefined>>, "settings"> = {
            action: {},
            bestiary: {},
            hazard: {},
            equipment: {},
            feat: {},
            spell: {},
        };

        // NPCs and Hazards are all loaded by default other packs can be set here.
        const loadDefault: Record<string, boolean | undefined> = {
            "pf2e.actionspf2e": true,
            "pf2e.equipment-srd": true,
            "pf2e.ancestryfeatures": true,
            "pf2e.classfeatures": true,
            "pf2e.feats-srd": true,
            "pf2e.spells-srd": true,
        };

        for (const pack of game.packs) {
            const types = new Set(pack.index.map((entry) => entry.type));
            if (types.size === 0) continue;

            if (types.has("npc")) {
                const load = this.settings.bestiary?.[pack.collection]?.load ?? true;
                settings.bestiary![pack.collection] = {
                    load,
                    name: pack.metadata.label,
                };
            }
            if (types.has("hazard")) {
                const load = this.settings.hazard?.[pack.collection]?.load ?? true;
                settings.hazard![pack.collection] = {
                    load,
                    name: pack.metadata.label,
                };
            }

            if (types.has("action")) {
                const load = this.settings.action?.[pack.collection]?.load ?? !!loadDefault[pack.collection];
                settings.action![pack.collection] = {
                    load,
                    name: pack.metadata.label,
                };
            } else if (
                ["weapon", "armor", "equipment", "consumable", "treasure", "backpack", "kit"].some((type) =>
                    types.has(type)
                )
            ) {
                const load = this.settings.equipment?.[pack.collection]?.load ?? !!loadDefault[pack.collection];
                settings.equipment![pack.collection] = {
                    load,
                    name: pack.metadata.label,
                };
            } else if (types.has("feat")) {
                const load = this.settings.feat?.[pack.collection]?.load ?? !!loadDefault[pack.collection];
                settings.feat![pack.collection] = {
                    load,
                    name: pack.metadata.label,
                };
            } else if (types.has("spell")) {
                const load = this.settings.spell?.[pack.collection]?.load ?? !!loadDefault[pack.collection];
                settings.spell![pack.collection] = {
                    load,
                    name: pack.metadata.label,
                };
            }
        }

        for (const tab of this.dataTabsList) {
            settings[tab] = Object.fromEntries(
                Object.entries(settings[tab]!).sort(([_collectionA, dataA], [_collectionB, dataB]) => {
                    return (dataA?.name ?? "") > (dataB?.name ?? "") ? 1 : -1;
                })
            );
        }

        this.settings = settings;
    }

    loadSettings() {
        this.settings = JSON.parse(game.settings.get("pf2e", "compendiumBrowserPacks"));
    }

    hookTab() {
        this.navigationTab = this._tabs[0];
        const tabCallback = this.navigationTab.callback;
        this.navigationTab.callback = async (event: JQuery.TriggeredEvent | null, tabs: Tabs, active: TabName) => {
            tabCallback?.(event, tabs, active);
            await this.loadTab(active);
        };
    }

    async openTab(tab: TabName, filter: string[] = [], maxLevel = 0): Promise<void> {
        this.initialFilter = filter;
        this.initialMaxLevel = maxLevel;
        await this._render(true);
        this.initialFilter = filter; // Reapply in case of a double-render (need to track those down)
        this.initialMaxLevel = maxLevel;
        this.navigationTab.activate(tab, { triggerCallback: true });
    }

    async loadTab(tab: TabName): Promise<void> {
        this.activeTab = tab;
        // Settings tab
        if (tab === "settings") {
            await this.render(true);
            return;
        }

        if (!this.dataTabsList.includes(tab)) {
            throw ErrorPF2e(`Unknown tab "${tab}"`);
        }

        // Initialize Tab if it is not already initialzed
        if (!this.tabs[tab]?.isInitialized) {
            await this.tabs[tab].init();
        }

        // Set filterData for this tab if intitial values were given
        if (this.initialFilter.length || this.initialMaxLevel) {
            const currentTab = this.tabs[tab];
            currentTab.resetFilters();
            for (const filter of this.initialFilter) {
                const [filterType, value] = filter.split("-");
                if (objectHasKey(currentTab.filterData.checkboxes, filterType)) {
                    const checkbox = currentTab.filterData.checkboxes[filterType];
                    const option = checkbox.options[value];
                    if (option) {
                        checkbox.isExpanded = true;
                        checkbox.selected.push(value);
                        option.selected = true;
                    } else {
                        console.warn(`Tab '${tab}' filter '${filterType}' has no option: '${value}'`);
                    }
                } else {
                    console.warn(`Tab '${tab}' has no filter '${filterType}'`);
                }
            }
            if (this.initialMaxLevel) {
                if (currentTab.filterData.ranges) {
                    const level = currentTab.filterData.ranges.level;
                    if (level) {
                        level.values.max = this.initialMaxLevel;
                    }
                }
            }
            this.initialFilter = [];
            this.initialMaxLevel = 0;
        }

        this.render(true);
    }

    loadedPacks(tab: TabName): string[] {
        if (tab === "settings") return [];
        return Object.entries(this.settings[tab] ?? []).flatMap(([collection, info]) => {
            return info?.load ? [collection] : [];
        });
    }

    override activateListeners($html: JQuery): void {
        super.activateListeners($html);
        const activeTabName = this.activeTab;

        // Settings Tab
        if (activeTabName === "settings") {
            $html.find<HTMLButtonElement>("button.save-settings").on("click", async () => {
                const formData = new FormData($html.find<HTMLFormElement>(".compendium-browser-settings form")[0]);
                for (const [t, packs] of Object.entries(this.settings) as [string, { [key: string]: PackInfo }][]) {
                    for (const [key, pack] of Object.entries(packs) as [string, PackInfo][]) {
                        pack.load = formData.has(`${t}-${key}`);
                    }
                }
                await game.settings.set("pf2e", "compendiumBrowserPacks", JSON.stringify(this.settings));
                this.loadSettings();
                this.initCompendiumList();
                for await (const tab of Object.values(this.tabs)) {
                    if (tab.isInitialized) {
                        await tab.init();
                        this.render(true);
                    }
                }
            });
            return;
        }
        // Other tabs
        const currentTab = this.tabs[activeTabName];
        const $controlArea = $html.find(".control-area");

        $controlArea.find("button.clear-filters").on("click", () => {
            this.resetFilters();
            this.clearScrollLimit();
            this.render(true);
        });

        // Toggle visibility of filter containers
        $controlArea.find(".filtercontainer h3").on("click", (event) => {
            const filterType = event.target.closest("div")?.dataset?.filterType;
            const filterName = event.target.closest("div")?.dataset?.filterName ?? "";
            if (filterType === "checkboxes" || filterType === "ranges") {
                const filters = currentTab.filterData[filterType];
                if (filters && objectHasKey(filters, filterName)) {
                    // This needs a type assertion because it resolves to never for some reason
                    const filter = filters[filterName] as CheckBoxdata | RangesData;
                    filter.isExpanded = !filter.isExpanded;
                    this.render(true);
                }
            }
        });

        // Sort item list
        const $sortContainer = $controlArea.find(".sortcontainer");
        const $orderSelects = $sortContainer.find<HTMLSelectElement>("select.order");
        const $directionButtons = $sortContainer.find("a.direction");
        $orderSelects.on("change", (event) => {
            const $order = $(event.target);
            const orderBy = $order.val()?.toString() ?? "name";
            currentTab.filterData.order.by = orderBy;
            this.clearScrollLimit();
            this.render(true);
        });

        $directionButtons.on("click", (event) => {
            const direction = ($(event.currentTarget).data("direction") as SortDirection) ?? "asc";
            currentTab.filterData.order.direction = direction === "asc" ? "desc" : "asc";
            this.clearScrollLimit();
            this.render(true);
        });

        // Search field
        $controlArea.find<HTMLInputElement>("input[name=textFilter]").on("change paste", (event) => {
            currentTab.filterData.search.text = event.target.value;
            this.clearScrollLimit();
            this.render(true);
        });

        // TODO: Support any generated select element
        $controlArea.find<HTMLSelectElement>(".timefilter select").on("change", (event) => {
            if (!currentTab.filterData?.dropdowns?.timefilter) return;
            currentTab.filterData.dropdowns.timefilter.selected = event.target.value;
            this.clearScrollLimit();
            this.render(true);
        });

        // Activate or deactivate filters
        $controlArea.find<HTMLInputElement>("input[type=checkbox]").on("click", (event) => {
            const checkboxName = event.target.closest("div")?.dataset?.filterName;
            const optionName = event.target.name;
            if (!checkboxName || !optionName) return;
            if (objectHasKey(currentTab.filterData.checkboxes, checkboxName)) {
                const checkbox = currentTab.filterData.checkboxes[checkboxName];
                const option = checkbox.options[optionName];
                option.selected = !option.selected;
                option.selected
                    ? checkbox.selected.push(optionName)
                    : (checkbox.selected = checkbox.selected.filter((name) => name !== optionName));
                this.clearScrollLimit();
                this.render(true);
            }
        });

        // Filter for levels
        $controlArea.find<HTMLInputElement>("input[name*=Bound]").on("keyup", (event) => {
            if (event.key !== "Enter") return;
            const $parent = $(event.target).closest("div");
            const name = ($parent.closest("div .filtercontainer").data("filterName") as string) ?? "";
            const ranges = currentTab.filterData.ranges;
            if (ranges && objectHasKey(ranges, name)) {
                const range = ranges[name];
                const $lowerBound = $parent.find<HTMLInputElement>("input[name*=lowerBound]");
                const $upperBound = $parent.find<HTMLInputElement>("input[name*=upperBound]");
                range.values.min = Number($lowerBound.val()) || 0;
                range.values.max = Number($upperBound.val()) || 0;
                this.clearScrollLimit();
                this.render(true);
            }
        });
    }

    /** Activate click listeners on loaded actors and items */
    private activateResultListeners(): void {
        const $list = this.element.find(".tab.active ul.item-list");
        if ($list.length === 0) return;

        const $items = $list.children("li");
        if ($list.data("listeners-active")) {
            $items.children("a").off("click");
        }

        $items
            .children(".name")
            .children("a.item-link, a.actor-link")
            .on("click", (event) => {
                const entry = $(event.currentTarget).closest(".item")[0].dataset;
                const id = entry.entryId ?? "";
                const compendium = entry.entryCompendium;
                const pack = game.packs.get(compendium ?? "");
                pack?.getDocument(id).then((document) => {
                    document!.sheet.render(true);
                });
            });

        // Add an item to selected tokens' actors' inventories
        $items.children("a.take-item").on("click", (event) => {
            const itemId = $(event.currentTarget).closest("li").attr("data-entry-id") ?? "";
            this.takePhysicalItem(itemId);
        });

        // Lazy load list when scrollbar reaches bottom
        $list.on("scroll", (event) => {
            const target = event.currentTarget;
            if (target.scrollTop + target.clientHeight === target.scrollHeight) {
                const tab = this.activeTab;
                if (tab === "settings") return;
                const currentValue = this.tabs[tab].scrollLimit;
                const maxValue = this.tabs[tab].totalItemCount ?? 0;
                if (currentValue < maxValue) {
                    const newValue = Math.clamped(currentValue + 100, 100, maxValue);
                    this.tabs[tab].scrollLimit = newValue;
                    this.render(true);
                }
            }
        });

        $list.data("listeners-active", true);
    }

    private async takePhysicalItem(itemId: string): Promise<void> {
        const actors: ActorPF2e[] = canvas.tokens.controlled.flatMap((token) =>
            token.actor?.isOwner && !(token.actor instanceof FamiliarPF2e) ? token.actor : []
        );
        if (actors.length === 0 && game.user.character) actors.push(game.user.character);
        if (actors.length === 0) {
            ui.notifications.error(game.i18n.format("PF2E.ErrorMessage.NoTokenSelected"));
            return;
        }

        const item = await this.getPhysicalItem(itemId);
        if (item instanceof KitPF2e) {
            for await (const actor of actors) await item.dumpContents(actor);
        } else {
            for await (const actor of actors) await actor.createEmbeddedDocuments("Item", [item.toObject()]);
        }

        if (actors.length === 1 && game.user.character && actors[0] === game.user.character) {
            ui.notifications.info(
                game.i18n.format("PF2E.CompendiumBrowser.AddedItemToCharacter", {
                    item: item.name,
                    character: game.user.character.name,
                })
            );
        } else {
            ui.notifications.info(game.i18n.format("PF2E.CompendiumBrowser.AddedItem", { item: item.name }));
        }
    }

    private async getPhysicalItem(itemId: string): Promise<PhysicalItemPF2e | KitPF2e> {
        const item = await game.packs.get("pf2e.equipment-srd")?.getDocument(itemId);
        if (!(item instanceof PhysicalItemPF2e || item instanceof KitPF2e)) {
            throw ErrorPF2e("Unexpected failure retrieving compendium item");
        }

        return item;
    }

    protected override _canDragStart() {
        return true;
    }

    protected override _canDragDrop() {
        return true;
    }

    /** Set drag data and lower opacity of the application window to reveal any tokens */
    protected override _onDragStart(event: ElementDragEvent): void {
        this.userIsDragging = true;
        this.element.animate({ opacity: 0.125 }, 250);

        const $item = $(event.currentTarget);
        const packName = $item.attr("data-entry-compendium");
        const itemPack = game.packs.find((pack) => pack.collection === packName);
        if (!itemPack) return;
        event.dataTransfer.setData(
            "text/plain",
            JSON.stringify({
                type: itemPack.documentName,
                pack: itemPack.collection,
                id: $item.attr("data-entry-id"),
            })
        );

        $item.one("dragend", () => {
            this.userIsDragging = false;
            this.element.animate({ opacity: 1 }, 500);
        });
    }

    /** Simulate a drop event on the DOM element directly beneath the compendium browser */
    protected override _onDrop(event: ElementDragEvent): void {
        if (!this.userIsDragging) return;

        // Get all elements beneath the compendium browser
        const browserZIndex = Number(this.element.css("zIndex"));
        const dropCandidates = Array.from(document.body.querySelectorAll("*")).filter(
            (element): element is HTMLElement => {
                if (!(element instanceof HTMLElement) || ["compendium-browser", "hud"].includes(element.id))
                    return false;
                const appBounds = element.getBoundingClientRect();
                const zIndex = Number(element.style.zIndex);
                if (!appBounds || zIndex > browserZIndex) return false;

                return (
                    event.clientX >= appBounds.left &&
                    event.clientX <= appBounds.right &&
                    event.clientY >= appBounds.top &&
                    event.clientY <= appBounds.bottom
                );
            }
        );

        const highestElement = dropCandidates.reduce((highest: HTMLElement | null, candidate) => {
            if (!highest) return candidate;
            return Number(candidate.style.zIndex) > Number(highest.style.zIndex) ? candidate : highest;
        }, null);

        if (highestElement) {
            const isSheet = /^actor-\w+$/.test(highestElement.id);
            const sheetForm = isSheet && highestElement.querySelector("form.editable");
            const dropTarget = isSheet && sheetForm instanceof HTMLElement ? sheetForm : highestElement;
            const newEvent = new DragEvent(event.type, {
                ...event,
                clientX: event.clientX,
                clientY: event.clientY,
                dataTransfer: new DataTransfer(),
            });
            newEvent.dataTransfer?.setData("text/plain", event.dataTransfer.getData("text/plain"));
            dropTarget.dispatchEvent(newEvent);
        }
    }

    injectActorDirectory() {
        const $html = ui.actors.element;
        if ($html.find(".bestiary-browser-btn").length > 0) return;

        // Bestiary Browser Buttons
        const bestiaryImportButton = $(
            `<button class="bestiary-browser-btn"><i class="fas fa-fire"></i> Bestiary Browser</button>`
        );

        if (game.user.isGM) {
            $html.find("footer").append(bestiaryImportButton);
        }

        // Handle button clicks
        bestiaryImportButton.on("click", (ev) => {
            ev.preventDefault();
            this.openTab("bestiary");
        });
    }

    override getData() {
        const activeTab = this.activeTab;
        // Settings
        if (activeTab === "settings") {
            return {
                user: game.user,
                settings: this.settings,
            };
        }
        // Active tab
        const tab = this.tabs[activeTab];
        if (tab) {
            return {
                user: game.user,
                [activeTab]: {
                    filterData: tab.filterData,
                    indexData: tab.getIndexData(),
                },
                scrollLimit: tab.scrollLimit,
            };
        }
        // No active tab
        return {
            user: game.user,
        };
    }

    private resetFilters(): void {
        const activeTab = this.activeTab;
        if (activeTab !== "settings") {
            this.tabs[activeTab].resetFilters();
        }
    }

    private clearScrollLimit() {
        const tab = this.activeTab;
        if (tab === "settings") return;

        const $list = this.element.find(".tab.active ul.item-list");
        $list.scrollTop(0);
        this.tabs[tab].scrollLimit = 100;
    }
}