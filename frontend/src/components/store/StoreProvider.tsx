"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  useTransition,
  type ReactNode,
} from "react";
import type { ProductListItem } from "@/lib/api/types";
import {
  addToCartAction,
  removeCartItemAction,
  updateCartItemAction,
  type ActionResult,
} from "@/lib/commerce/actions";
import type { Cart } from "@/lib/commerce/types";

// Shopping state shared by the header, product pages and the cart.
//
// Cart — one source of truth at a time:
// - Signed in: the cart saved in PostgreSQL. Every change goes through the API
//   (Server Actions) and the UI shows the cart the API returns, so a reload,
//   logout/login or another device shows the same cart.
// - Guest: a temporary cart in browser memory (lost on a full page reload).
//   It is merged into the saved cart when the shopper logs in or registers.
//
// Favorites stay in browser memory for now.

/** One cart line = one real backend ProductVariant. */
export interface CartItem {
  variantId: number;
  /** Saved-cart line id (signed-in customers only). */
  cartItemId?: number;
  sku: string;
  productId: number;
  productSlug: string;
  productName: string;
  categorySlug: string;
  colorName: string;
  /** Null for one-size products. */
  size: string | null;
  /** Variant effective price from the API, whole FCFA. */
  unitPrice: number;
  image: { src: string; alt: string } | null;
  /** Available stock (current for saved carts, a snapshot for guest carts). */
  availableQuantity: number;
  quantity: number;
  /** Why the line can't be ordered right now (saved carts only). */
  issue?: string | null;
}

export type CartResult = { ok: true } | { ok: false; message: string; code: string };

const MAX_QUANTITY = 10;

/** Highest quantity allowed for a line: its stock, capped at 10. */
export function maxQuantity(availableQuantity: number): number {
  return Math.max(0, Math.min(MAX_QUANTITY, availableQuantity));
}

function linesFromServer(cart: Cart | null): CartItem[] {
  if (!cart) return [];
  return cart.items.map((line) => ({
    variantId: line.variant.id,
    cartItemId: line.cart_item_id,
    sku: line.variant.sku,
    productId: line.product.id,
    productSlug: line.product.slug,
    productName: line.product.name,
    categorySlug: line.product.category_slug,
    colorName: line.variant.color_name,
    size: line.variant.size,
    unitPrice: line.unit_price,
    image: line.product.image
      ? { src: line.product.image.image_path, alt: line.product.image.alt_text }
      : null,
    availableQuantity: line.available_quantity,
    quantity: line.quantity,
    issue: line.issue,
  }));
}

interface StoreValue {
  favorites: ReadonlyMap<string, ProductListItem>;
  isFavorite: (slug: string) => boolean;
  toggleFavorite: (product: ProductListItem) => void;
  /** True when the cart is the customer's saved cart. */
  signedIn: boolean;
  /** The saved cart couldn't be loaded (API unreachable). */
  cartUnavailable: boolean;
  cart: CartItem[];
  cartCount: number;
  /** A saved-cart change is being sent to the API. */
  cartPending: boolean;
  /** Adds a line (or more of an existing one), within available stock. */
  addToCart: (item: CartItem) => Promise<CartResult>;
  setQuantity: (variantId: number, quantity: number) => Promise<CartResult>;
  removeFromCart: (variantId: number) => Promise<CartResult>;
}

const StoreContext = createContext<StoreValue | null>(null);

export function StoreProvider({
  children,
  signedIn,
  serverCart,
}: {
  children: ReactNode;
  signedIn: boolean;
  /** The saved cart from the server render; "unavailable" if it failed. */
  serverCart: Cart | "unavailable" | null;
}) {
  const [favorites, setFavorites] = useState<ReadonlyMap<string, ProductListItem>>(new Map());
  const [guestCart, setGuestCart] = useState<CartItem[]>([]);
  const [pending, startTransition] = useTransition();

  // The saved cart shown on screen. It is replaced whenever the server renders
  // a newer one (login, checkout, refresh) or an action returns one.
  const initial = serverCart === "unavailable" ? null : serverCart;
  const [saved, setSaved] = useState({ from: serverCart, lines: linesFromServer(initial) });
  if (saved.from !== serverCart) {
    setSaved({ from: serverCart, lines: linesFromServer(initial) });
  }

  // After login the guest cart has been merged into the saved cart: drop it.
  const [wasSignedIn, setWasSignedIn] = useState(signedIn);
  if (wasSignedIn !== signedIn) {
    setWasSignedIn(signedIn);
    if (signedIn) setGuestCart([]);
  }

  const cart = signedIn ? saved.lines : guestCart;

  const toggleFavorite = useCallback((product: ProductListItem) => {
    setFavorites((current) => {
      const next = new Map(current);
      if (next.has(product.slug)) next.delete(product.slug);
      else next.set(product.slug, product);
      return next;
    });
  }, []);

  /** Runs a saved-cart action and shows the cart it returns. */
  const runCartAction = useCallback(
    (action: () => Promise<ActionResult<Cart>>): Promise<CartResult> =>
      new Promise((resolve) => {
        startTransition(async () => {
          const result = await action();
          if (result.ok) {
            setSaved((current) => ({
              from: current.from,
              lines: linesFromServer(result.data),
            }));
            resolve({ ok: true });
          } else {
            resolve({ ok: false, message: result.message, code: result.code });
          }
        });
      }),
    [],
  );

  const addToCart = useCallback(
    async (item: CartItem): Promise<CartResult> => {
      if (signedIn) {
        return runCartAction(() => addToCartAction(item.variantId, item.quantity));
      }
      setGuestCart((current) => {
        const existing = current.find((line) => line.variantId === item.variantId);
        const limit = maxQuantity(item.availableQuantity);
        if (!existing) {
          return [...current, { ...item, quantity: Math.min(item.quantity, limit) }];
        }
        return current.map((line) =>
          line === existing
            ? { ...item, quantity: Math.min(limit, line.quantity + item.quantity) }
            : line,
        );
      });
      return { ok: true };
    },
    [signedIn, runCartAction],
  );

  const setQuantity = useCallback(
    async (variantId: number, quantity: number): Promise<CartResult> => {
      if (signedIn) {
        const line = saved.lines.find((l) => l.variantId === variantId);
        if (!line?.cartItemId) return { ok: false, code: "missing", message: "Item not found." };
        const itemId = line.cartItemId;
        return runCartAction(() => updateCartItemAction(itemId, quantity));
      }
      setGuestCart((current) =>
        current.map((line) =>
          line.variantId === variantId
            ? {
                ...line,
                quantity: Math.max(1, Math.min(maxQuantity(line.availableQuantity), quantity)),
              }
            : line,
        ),
      );
      return { ok: true };
    },
    [signedIn, saved.lines, runCartAction],
  );

  const removeFromCart = useCallback(
    async (variantId: number): Promise<CartResult> => {
      if (signedIn) {
        const line = saved.lines.find((l) => l.variantId === variantId);
        if (!line?.cartItemId) return { ok: false, code: "missing", message: "Item not found." };
        const itemId = line.cartItemId;
        return runCartAction(() => removeCartItemAction(itemId));
      }
      setGuestCart((current) => current.filter((line) => line.variantId !== variantId));
      return { ok: true };
    },
    [signedIn, saved.lines, runCartAction],
  );

  const value = useMemo<StoreValue>(
    () => ({
      favorites,
      isFavorite: (slug) => favorites.has(slug),
      toggleFavorite,
      signedIn,
      cartUnavailable: signedIn && serverCart === "unavailable",
      cart,
      cartCount: cart.reduce((sum, line) => sum + line.quantity, 0),
      cartPending: pending,
      addToCart,
      setQuantity,
      removeFromCart,
    }),
    [
      favorites,
      toggleFavorite,
      signedIn,
      serverCart,
      cart,
      pending,
      addToCart,
      setQuantity,
      removeFromCart,
    ],
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): StoreValue {
  const store = useContext(StoreContext);
  if (!store) throw new Error("useStore must be used inside <StoreProvider>");
  return store;
}

/** How many of a variant are already in the cart. */
export function useCartQuantity(variantId: number | undefined): number {
  const { cart } = useStore();
  if (variantId === undefined) return 0;
  return cart.find((line) => line.variantId === variantId)?.quantity ?? 0;
}
