import { useEffect, useRef, useState } from "react";

export interface UseInViewOptions {
  rootMargin?: string;
  threshold?: number;
  /** Stop observing after the first intersection (default true). */
  once?: boolean;
}

/**
 * `[ref, inView]` via IntersectionObserver. Once-only by default. Falls back to
 * `inView = true` immediately when IntersectionObserver is undefined (jsdom/SSR),
 * so content is never permanently hidden.
 */
export function useInView<T extends Element = HTMLDivElement>(
  options: UseInViewOptions = {},
): [React.RefObject<T>, boolean] {
  const { rootMargin = "0px", threshold = 0, once = true } = options;
  const ref = useRef<T>(null);
  const [inView, setInView] = useState<boolean>(
    () => typeof IntersectionObserver === "undefined",
  );

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting) {
          setInView(true);
          if (once) observer.disconnect();
        } else if (!once) {
          setInView(false);
        }
      },
      { rootMargin, threshold },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [rootMargin, threshold, once]);

  return [ref, inView];
}

export default useInView;
