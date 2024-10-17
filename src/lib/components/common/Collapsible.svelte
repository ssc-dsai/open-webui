<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();
	$: dispatch('change', open);

	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';

	export let open = false;
	export let className = '';
	export let buttonClassName = 'w-fit';
	export let title = null;

	let contentHeight = 0;
	let contentElement: HTMLElement;

	function handleClick(event) {
		if (!event.target.closest('.no-toggle')) {
			open = !open;
		}
	}

	$: if (contentElement) {
		contentHeight = open ? contentElement.scrollHeight : 0;
	}
</script>

<div class={className}>
	{#if title !== null}
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<div class={buttonClassName} on:pointerup={() => (open = !open)}>
			<div class=" w-fit font-medium transition flex items-center justify-between gap-2">
				<div>
					{title}
				</div>

				<div>
					{#if open}
						<ChevronUp strokeWidth="3.5" className="size-3.5" />
					{:else}
						<ChevronDown strokeWidth="3.5" className="size-3.5" />
					{/if}
				</div>
			</div>
		</div>
	{:else}
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<div class={buttonClassName} on:pointerup={() => (open = !open)}>
			<div
				class="flex items-center gap-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
			>
				<slot />
			</div>
		</div>
	{/if}

	<div
		bind:this={contentElement}
		class="overflow-hidden transition-all duration-300 ease-in-out"
		style="max-height: {contentHeight}px;"
	>
		<div>
			<slot name="content" />
		</div>
	</div>
</div>
