# Animation Guide for PurposePath Components

This guide explains how to add smooth animations to new components in the PurposePath project using Framer Motion.

## Overview

PurposePath uses Framer Motion for all animations to ensure consistent, performant, and accessible transitions throughout the application. The animation system focuses on:

- Smooth scene transitions (fade out → fade in)
- Media element animations (images, dialogue bubbles)
- Interactive button animations (hover, tap effects)
- Responsive layouts with GPU-accelerated transforms

## Basic Setup

### 1. Import Framer Motion

```typescript
import { motion, AnimatePresence } from 'framer-motion';
```

### 2. Define Animation Variants

Create reusable animation variants for consistent behavior:

```typescript
const fadeInVariants = {
  initial: { 
    opacity: 0, 
    y: 20,
    scale: 0.95
  },
  animate: { 
    opacity: 1, 
    y: 0,
    scale: 1,
    transition: {
      duration: 0.6,
      ease: [0.25, 0.46, 0.45, 0.94] // Custom easing curve
    }
  },
  exit: { 
    opacity: 0, 
    y: -20,
    scale: 0.95,
    transition: {
      duration: 0.4,
      ease: [0.25, 0.46, 0.45, 0.94]
    }
  }
}
```

## Common Animation Patterns

### Scene Transitions

For components that need to transition between different states/scenes:

```typescript
<AnimatePresence mode="wait">
  <motion.div
    key={uniqueKey} // Important: changes trigger re-animation
    variants={sceneVariants}
    initial="initial"
    animate="animate"
    exit="exit"
  >
    {content}
  </motion.div>
</AnimatePresence>
```

### Image Loading Animations

For images that should animate in when loaded:

```typescript
const imageVariants = {
  initial: { 
    opacity: 0, 
    scale: 0.8,
    filter: 'blur(4px)'
  },
  animate: { 
    opacity: 1, 
    scale: 1,
    filter: 'blur(0px)',
    transition: {
      duration: 0.8,
      ease: [0.25, 0.46, 0.45, 0.94],
      delay: 0.2
    }
  }
}

<motion.img
  variants={imageVariants}
  initial="initial"
  animate={imageLoaded ? "animate" : "initial"}
  onLoad={() => setImageLoaded(true)}
  style={{ willChange: 'transform, opacity, filter' }}
/>
```

### Interactive Button Animations

For buttons with hover and tap effects:

```typescript
const buttonVariants = {
  hover: { 
    scale: 1.02,
    y: -2,
    boxShadow: '0 8px 25px rgba(0,0,0,0.15)',
    transition: {
      duration: 0.2,
      ease: 'easeInOut'
    }
  },
  tap: { 
    scale: 0.98,
    transition: {
      duration: 0.1
    }
  }
}

<motion.button
  variants={buttonVariants}
  whileHover="hover"
  whileTap="tap"
  style={{ willChange: 'transform, box-shadow' }}
>
  Click me
</motion.button>
```

### Dialogue/Pop-up Animations

For components that should "pop" into view:

```typescript
const popVariants = {
  initial: { 
    opacity: 0, 
    scale: 0.8,
    y: 10
  },
  animate: { 
    opacity: 1, 
    scale: 1,
    y: 0,
    transition: {
      type: "spring",
      damping: 20,
      stiffness: 300,
      duration: 0.6
    }
  }
}
```

## Performance Best Practices

### 1. Use `willChange` CSS Property

Always add `willChange` for properties that will be animated:

```typescript
style={{ willChange: 'transform, opacity, filter' }}
```

### 2. Prefer Transform and Opacity

These properties are GPU-accelerated:
- ✅ `transform`, `opacity`, `filter`
- ❌ `width`, `height`, `top`, `left`

### 3. Use Layout Animations Sparingly

Only use `layout` prop when necessary as it can be expensive:

```typescript
<motion.div layout> // Use only when needed
```

### 4. Optimize Animation Timing

- Keep transitions under 0.8s for scene changes
- Use 0.2-0.3s for hover effects
- Use 0.1s for tap/click feedback

## Responsive Considerations

### Mobile Optimization

- Reduce animation complexity on smaller screens
- Consider `prefers-reduced-motion` media query
- Test on actual devices for performance

### Desktop Enhancements

- Add more subtle hover effects
- Use parallax-style movements
- Implement keyboard navigation animations

## Accessibility

### Respect User Preferences

```typescript
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

const variants = {
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: prefersReducedMotion.matches ? 0 : 0.6
    }
  }
}
```

### Focus Management

Ensure animations don't interfere with keyboard navigation:

```typescript
<motion.button
  whileFocus={{ scale: 1.05 }}
  // Focus ring should still be visible
/>
```

## Component Integration Examples

### Adding Animation to a New Scene Component

```typescript
import { motion, AnimatePresence } from 'framer-motion';

export default function NewSceneComponent() {
  const [sceneKey, setSceneKey] = useState(0);
  
  const sceneVariants = {
    initial: { opacity: 0, y: 20, scale: 0.95 },
    animate: { 
      opacity: 1, 
      y: 0, 
      scale: 1,
      transition: { duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }
    },
    exit: { 
      opacity: 0, 
      y: -20, 
      scale: 0.95,
      transition: { duration: 0.4 }
    }
  };

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={sceneKey}
        variants={sceneVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        className="p-8 max-w-xl mx-auto"
      >
        {/* Your scene content */}
      </motion.div>
    </AnimatePresence>
  );
}
```

## Testing Animations

### Mock Framer Motion in Tests

```typescript
// In test files
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));
```

### Test Animation Structure

```typescript
test('component has proper animation structure', () => {
  render(<AnimatedComponent />);
  
  const motionDiv = screen.getByTestId('motion-div');
  expect(motionDiv).toBeInTheDocument();
  
  // Test that disabled states work during animations
  const button = screen.getByRole('button');
  fireEvent.click(button);
  expect(button).toBeDisabled(); // During transition
});
```

## Common Gotchas

1. **Key Changes**: Always use a changing `key` prop for scene transitions
2. **State Timing**: Update state after exit animations complete (use `setTimeout`)
3. **Z-Index Issues**: Use `style={{ zIndex: 1 }}` for overlapping animated elements
4. **Memory Leaks**: Clean up animation timers in `useEffect` cleanup functions

## Animation Hierarchy

1. **Page/Scene Level**: 0.6-0.8s fade transitions
2. **Component Level**: 0.4-0.6s enter/exit animations  
3. **Element Level**: 0.2-0.4s hover/focus states
4. **Micro-interactions**: 0.1-0.2s button presses

This hierarchy ensures animations feel coordinated and natural throughout the application.