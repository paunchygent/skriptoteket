export type CatalogItemBase = {
  id: string;
  title: string;
  summary: string | null;
  is_favorite: boolean;
};

export type CatalogToolItem = CatalogItemBase & {
  kind: "tool";
  slug: string;
};

export type CatalogCuratedAppItem = CatalogItemBase & {
  kind: "curated_app";
  app_id: string;
};

export type CatalogItem = CatalogToolItem | CatalogCuratedAppItem;
