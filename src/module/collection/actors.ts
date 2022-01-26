import { ActorPF2e } from "@actor";
import { ActorUpdateContext } from "@actor/base";

export class ActorsPF2e<TActor extends ActorPF2e = ActorPF2e> extends Actors<TActor> {
    /** Work around a bug as of Foundry V9.242 in which token default settings are ignored for compendium imports */
    override fromCompendium(actor: TActor | TActor["data"]["_source"], options?: FromCompendiumOptions) {
        const defaultToken = game.settings.get("core", "defaultToken");
        delete defaultToken.disposition;

        if (actor instanceof ActorPF2e) {
            actor.data.update({ token: defaultToken });
        } else {
            mergeObject(actor, { token: defaultToken });
        }

        return super.fromCompendium(actor, options);
    }

    /** Ditto */
    override async importFromCompendium(
        pack: CompendiumCollection<TActor>,
        actorId: string,
        updateData?: DocumentUpdateData<TActor>,
        options?: ActorUpdateContext<TActor>
    ): Promise<TActor | null> {
        const actor = await super.importFromCompendium(pack, actorId, updateData, options);
        if (!actor) return actor;

        const defaultToken = game.settings.get("core", "defaultToken");
        delete defaultToken.disposition;

        actor.data.update({ token: defaultToken });

        return actor;
    }
}