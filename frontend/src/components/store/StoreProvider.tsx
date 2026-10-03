"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

// Frontend-only shopping state (favorites + cart). It lives in memory for the
// browser session: it survives page navigation but not a full page reload,
// and nothing is sent to a server yet.

export interface CartItem {
  slug: string;
  colorSlug: string;
  /** Undefined for one-size products. */
  size?: string;
  quantity: number;
}

export const cartItemKey = (item: Omit<CartItem, "quantity">) =>
  `${item.slug}:${item.colorSlug}:${item.size ?? "one-size"}`;

const MAX_QUANTITY = 10;

interface StoreValue {
  favorites: ReadonlySet<string>;
  isFavorite: (slug: string) => boolean;
  toggleFavorite: (slug: string) => void;
  cart: CartItem[];
  cartCount: number;
  addToCart: (item: CartItem) => void;
  setQuantity: (key: string, quantity: number) => void;
  removeFromCart: (key: string) => void;
}

const StoreContext = createContext<StoreValue | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [favorites, setFavorites] = useState<ReadonlySet<string>>(new Set());
  const [cart, setCart] = useState<CartItem[]>([]);

  const toggleFavorite = useCallback((slug: string) => {
    setFavorites((current) => {
      const next = new Set(current);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  }, []);

  const addToCart = useCallback((item: CartItem) => {
    setCart((current) => {
      const key = cartItemKey(item);
      const existing = current.find((line) => cartItemKey(line) === key);
      if (!existing) return [...current, item];
      return current.map((line) =>
        line === existing
          ? {
              ...line,
              quantity: Math.min(MAX_QUANTITY, line.quantity + item.quantity),
            }
          : line,
      );
    });
  }, []);

  const setQuantity = useCallback((key: string, quantity: number) => {
    setCart((current) =>
      current.map((line) =>
        cartItemKey(line) === key
          ? { ...line, quantity: Math.max(1, Math.min(MAX_QUANTITY, quantity)) }
          : line,
      ),
    );
  }, []);

  const removeFromCart = useCallback((key: string) => {
    setCart((current) => current.filter((line) => cartItemKey(line) !== key));
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
