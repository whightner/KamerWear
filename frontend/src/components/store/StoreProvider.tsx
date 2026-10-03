"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { ProductListItem } from "@/lib/api/types";

// Frontend-only shopping state (favorites + cart). It lives in memory for the
// browser session: it survives page navigation but not a full page reload,
// and nothing is sent to a server yet.

/** One cart line = one real backend ProductVariant. */
export interface CartItem {
  variantId: number;
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
  /** API availability when the item was added; the quantity never exceeds it. */
  availableQuantity: number;
  quantity: number;
}

const MAX_QUANTITY = 10;

/** Highest quantity allowed for a line: its stock snapshot, capped at 10. */
export function maxQuantity(availableQuantity: number): number {
  return Math.max(0, Math.min(MAX_QUANTITY, availableQuantity));
}

interface StoreValue {
  favorites: ReadonlyMap<string, ProductListItem>;
  isFavorite: (slug: string) => boolean;
  toggleFavorite: (product: ProductListItem) => void;
  cart: CartItem[];
  cartCount: number;
  /** Adds a line (or more of an existing one), capped by available stock. */
  addToCart: (item: CartItem) => void;
  setQuantity: (variantId: number, quantity: number) => void;
  removeFromCart: (variantId: number) => void;
}

const StoreContext = createContext<StoreValue | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [favorites, setFavorites] = useState<
    ReadonlyMap<string, ProductListItem>
  >(new Map());
  const [cart, setCart] = useState<CartItem[]>([]);

  const toggleFavorite = useCallback((product: ProductListItem) => {
    setFavorites((current) => {
      const next = new Map(current);
      if (next.has(product.slug)) next.delete(product.slug);
      else next.set(product.slug, product);
      return next;
    });
  }, []);

  const addToCart = useCallback((item: CartItem) => {
    setCart((current) => {
      const existing = current.find(
        (line) => line.variantId === item.variantId,
      );
      const limit = maxQuantity(item.availableQuantity);
      if (!existing) {
        return [
          ...current,
          { ...item, quantity: Math.min(item.quantity, limit) },
        ];
      }
      return current.map((line) =>
        line === existing
          ? {
              ...item,
              quantity: Math.min(limit, line.quantity + item.quantity),
            }
          : line,
      );
    });
  }, []);

  const setQuantity = useCallback((variantId: number, quantity: number) => {
    setCart((current) =>
      current.map((line) =>
        line.variantId === variantId
          ? {
              ...line,
              quantity: Math.max(
                1,
                Math.min(maxQuantity(line.availableQuantity), quantity),
              ),
            }
          : line,
      ),
    );
  }, []);

  const removeFromCart = useCallback((variantId: number) => {
    setCart((current) =>
      current.filter((line) => line.variantId !== variantId),
    );
  }, []);

  const value = useMemo<StoreValue>(
    () => ({
      favorites,
      isFavorite: (slug) => favorites.has(slug),
      toggleFavorite,
      cart,
      cartCount: cart.reduce((sum, line) => sum + line.quantity, 0),
      addToCart,
      setQuantity,
      removeFromCart,
    }),
    [favorites, toggleFavorite, cart, addToCart, setQuantity, removeFromCart],
  );

  return (
    <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
  );
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
