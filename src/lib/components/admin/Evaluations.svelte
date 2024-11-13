<script>
	import { getContext, tick, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Leaderboard from './Evaluations/Leaderboard.svelte';
	import Feedbacks from './Evaluations/Feedbacks.svelte';

	import { getAllFeedbacks } from '$lib/apis/evaluations';

	const i18n = getContext('i18n');

	let selectedTab = 'leaderboard';

	let query = '';
	let page = 1;

	let tagEmbeddings = new Map();

	let loaded = false;
	let loadingLeaderboard = true;
	let debounceTimer;

	$: paginatedFeedbacks = feedbacks.slice((page - 1) * 10, page * 10);

	type Feedback = {
		id: string;
		data: {
			rating: number;
			model_id: string;
			sibling_model_ids: string[] | null;
			reason: string;
			comment: string;
			tags: string[];
		};
		user: {
			name: string;
			profile_image_url: string;
		};
		updated_at: number;
	};

	type ModelStats = {
		rating: number;
		won: number;
		lost: number;
	};

	//////////////////////
	//
	// Rank models by Elo rating
	//
	//////////////////////

	const rankHandler = async (similarities: Map<string, number> = new Map()) => {
		const modelStats = calculateModelStats(feedbacks, similarities);

		rankedModels = $models
			.filter((m) => m?.owned_by !== 'arena' && (m?.info?.meta?.hidden ?? false) !== true)
			.map((model) => {
				const stats = modelStats.get(model.id);
				return {
					...model,
					rating: stats ? Math.round(stats.rating) : '-',
					stats: {
						count: stats ? stats.won + stats.lost : 0,
						won: stats ? stats.won.toString() : '-',
						lost: stats ? stats.lost.toString() : '-'
					}
				};
			})
			.sort((a, b) => {
				if (a.rating === '-' && b.rating !== '-') return 1;
				if (b.rating === '-' && a.rating !== '-') return -1;
				if (a.rating !== '-' && b.rating !== '-') return b.rating - a.rating;
				return a.name.localeCompare(b.name);
			});

		loadingLeaderboard = false;
	};

	function calculateModelStats(
		feedbacks: Feedback[],
		similarities: Map<string, number>
	): Map<string, ModelStats> {
		const stats = new Map<string, ModelStats>();
		const K = 32;

		function getOrDefaultStats(modelId: string): ModelStats {
			return stats.get(modelId) || { rating: 1000, won: 0, lost: 0 };
		}

		function updateStats(modelId: string, ratingChange: number, outcome: number) {
			const currentStats = getOrDefaultStats(modelId);
			currentStats.rating += ratingChange;
			if (outcome === 1) currentStats.won++;
			else if (outcome === 0) currentStats.lost++;
			stats.set(modelId, currentStats);
		}

		function calculateEloChange(
			ratingA: number,
			ratingB: number,
			outcome: number,
			similarity: number
		): number {
			const expectedScore = 1 / (1 + Math.pow(10, (ratingB - ratingA) / 400));
			return K * (outcome - expectedScore) * similarity;
		}

		feedbacks.forEach((feedback) => {
			const modelA = feedback.data.model_id;
			const statsA = getOrDefaultStats(modelA);
			let outcome: number;

			switch (feedback.data.rating.toString()) {
				case '1':
					outcome = 1;
					break;
				case '-1':
					outcome = 0;
					break;
				default:
					return; // Skip invalid ratings
			}

			// If the query is empty, set similarity to 1, else get the similarity from the map
			const similarity = query !== '' ? similarities.get(feedback.id) || 0 : 1;
			const opponents = feedback.data.sibling_model_ids || [];

			opponents.forEach((modelB) => {
				const statsB = getOrDefaultStats(modelB);
				const changeA = calculateEloChange(statsA.rating, statsB.rating, outcome, similarity);
				const changeB = calculateEloChange(statsB.rating, statsA.rating, 1 - outcome, similarity);

				updateStats(modelA, changeA, outcome);
				updateStats(modelB, changeB, 1 - outcome);
			});
		});

		return stats;
	}

	let loaded = false;
	let feedbacks = [];

	const shareHandler = async () => {
		toast.success($i18n.t('Redirecting you to OpenWebUI Community'));

		// remove snapshot from feedbacks
		const feedbacksToShare = feedbacks.map((f) => {
			const { snapshot, user, ...rest } = f;
			return rest;
		});
		console.log(feedbacksToShare);

		const url = 'https://openwebui.com';
		const tab = await window.open(`${url}/leaderboard`, '_blank');

		// Define the event handler function
		const messageHandler = (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(feedbacksToShare), '*');

				// Remove the event listener after handling the message
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
	};

	onMount(async () => {
		feedbacks = await getAllFeedbacks(localStorage.token);
		loaded = true;

		const containerElement = document.getElementById('users-tabs-container');

		if (containerElement) {
			containerElement.addEventListener('wheel', function (event) {
				if (event.deltaY !== 0) {
					// Adjust horizontal scroll position based on vertical scroll
					containerElement.scrollLeft += event.deltaY;
				}
			});
		}
	});
</script>

{#if loaded}
	<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
		<div
			id="users-tabs-container"
			class="tabs flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-40 dark:text-gray-200 text-sm font-medium text-left scrollbar-none"
		>
			<button
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab ===
				'leaderboard'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedTab = 'leaderboard';
				}}
			>
				<div class=" self-center mr-2">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm6 5.75a.75.75 0 0 1 1.5 0v3.5a.75.75 0 0 1-1.5 0v-3.5Zm-2.75 1.5a.75.75 0 0 1 1.5 0v2a.75.75 0 0 1-1.5 0v-2Zm-2 .75a.75.75 0 0 0-.75.75v.5a.75.75 0 0 0 1.5 0v-.5a.75.75 0 0 0-.75-.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center">{$i18n.t('Leaderboard')}</div>
			</button>

			<button
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab ===
				'feedbacks'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedTab = 'feedbacks';
				}}
			>
				<div class=" self-center mr-2">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M5.25 2A2.25 2.25 0 0 0 3 4.25v9a.75.75 0 0 0 1.183.613l1.692-1.195 1.692 1.195a.75.75 0 0 0 .866 0l1.692-1.195 1.693 1.195A.75.75 0 0 0 13 13.25v-9A2.25 2.25 0 0 0 10.75 2h-5.5Zm3.03 3.28a.75.75 0 0 0-1.06-1.06L4.97 6.47a.75.75 0 0 0 0 1.06l2.25 2.25a.75.75 0 0 0 1.06-1.06l-.97-.97h1.315c.76 0 1.375.616 1.375 1.375a.75.75 0 0 0 1.5 0A2.875 2.875 0 0 0 8.625 6.25H7.311l.97-.97Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center">{$i18n.t('Feedbacks')}</div>
			</button>
		</div>

		<div class="flex-1 mt-1 lg:mt-0 overflow-y-scroll">
			{#if selectedTab === 'leaderboard'}
				<Leaderboard {feedbacks} />
			{:else if selectedTab === 'feedbacks'}
				<Feedbacks {feedbacks} />
			{/if}
		</div>

		<div class=" flex space-x-2">
			<Tooltip content={$i18n.t('Re-rank models by topic similarity')}>
				<div class="flex flex-1">
					<div class=" self-center ml-1 mr-3">
						<MagnifyingGlass className="size-3" />
					</div>
					<input
						class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-none bg-transparent"
						bind:value={query}
						placeholder={$i18n.t('Search')}
						on:focus={() => {
							loadEmbeddingModel();
						}}
					/>
				</div>
			</Tooltip>
		</div>
	</div>

	<div
		class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5"
	>
		{#if loadingLeaderboard}
			<div class=" absolute top-0 bottom-0 left-0 right-0 flex">
				<div class="m-auto">
					<Spinner />
				</div>
			</div>
		{/if}
		{#if (rankedModels ?? []).length === 0}
			<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-1">
				{$i18n.t('No models found')}
			</div>
		{:else}
			<table
				class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded {loadingLeaderboard
					? 'opacity-20'
					: ''}"
			>
				<thead
					class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
				>
					<tr class="">
						<th scope="col" class="px-3 py-1.5 cursor-pointer select-none w-3">
							{$i18n.t('RK')}
						</th>
						<th scope="col" class="px-3 py-1.5 cursor-pointer select-none">
							{$i18n.t('Model')}
						</th>
						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-fit">
							{$i18n.t('Rating')}
						</th>
						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-5">
							{$i18n.t('Won')}
						</th>
						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-5">
							{$i18n.t('Lost')}
						</th>
					</tr>
				</thead>
				<tbody class="">
					{#each rankedModels as model, modelIdx (model.id)}
						<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs group">
							<td class="px-3 py-1.5 text-left font-medium text-gray-900 dark:text-white w-fit">
								<div class=" line-clamp-1">
									{model?.rating !== '-' ? modelIdx + 1 : '-'}
								</div>
							</td>
							<td class="px-3 py-1.5 flex flex-col justify-center">
								<div class="flex items-center gap-2">
									<div class="flex-shrink-0">
										<img
											src={model?.info?.meta?.profile_image_url ?? '/favicon.png'}
											alt={model.name}
											class="size-5 rounded-full object-cover shrink-0"
										/>
									</div>

									<div class="font-medium text-gray-800 dark:text-gray-200 pr-4">
										{model.name}
									</div>
								</div>
							</td>
							<td class="px-3 py-1.5 text-right font-medium text-gray-900 dark:text-white w-max">
								{model.rating}
							</td>

							<td class=" px-3 py-1.5 text-right font-semibold text-green-500">
								<div class=" w-10">
									{#if model.stats.won === '-'}
										-
									{:else}
										<span class="hidden group-hover:inline"
											>{((model.stats.won / model.stats.count) * 100).toFixed(1)}%</span
										>
										<span class=" group-hover:hidden">{model.stats.won}</span>
									{/if}
								</div>
							</td>

							<td class="px-3 py-1.5 text-right font-semibold text-red-500">
								<div class=" w-10">
									{#if model.stats.lost === '-'}
										-
									{:else}
										<span class="hidden group-hover:inline"
											>{((model.stats.lost / model.stats.count) * 100).toFixed(1)}%</span
										>
										<span class=" group-hover:hidden">{model.stats.lost}</span>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>

	<div class=" text-gray-500 text-xs mt-1.5 w-full flex justify-end">
		<div class=" text-right">
			<div class="line-clamp-1">
				ⓘ {$i18n.t(
					'The evaluation leaderboard is based on the Elo rating system and is updated in real-time.'
				)}
			</div>
			{$i18n.t(
				'The leaderboard is currently in beta, and we may adjust the rating calculations as we refine the algorithm.'
			)}
		</div>
	</div>

	<div class="pb-4"></div>

	<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
		<div class="flex md:self-center text-lg font-medium px-0.5">
			{$i18n.t('Feedback History')}

			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />

			<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{feedbacks.length}</span>
		</div>

		<div>
			<div>
				<Tooltip content={$i18n.t('Export')}>
					<button
						class=" p-2 rounded-xl hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition font-medium text-sm flex items-center space-x-1"
						on:click={() => {
							exportHandler();
						}}
					>
						<path
							d="M8.5 4.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0ZM10.9 12.006c.11.542-.348.994-.9.994H2c-.553 0-1.01-.452-.902-.994a5.002 5.002 0 0 1 9.803 0ZM14.002 12h-1.59a2.556 2.556 0 0 0-.04-.29 6.476 6.476 0 0 0-1.167-2.603 3.002 3.002 0 0 1 3.633 1.911c.18.522-.283.982-.836.982ZM12 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"
						/>
					</svg>
				</div>
				<div class=" self-center">{$i18n.t('Leaderboard')}</div>
			</button>

			<button
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab ===
				'feedbacks'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedTab = 'feedbacks';
				}}
			>
				<div class=" self-center mr-2">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							d="M8 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM3.156 11.763c.16-.629.44-1.21.813-1.72a2.5 2.5 0 0 0-2.725 1.377c-.136.287.102.58.418.58h1.449c.01-.077.025-.156.045-.237ZM12.847 11.763c.02.08.036.16.046.237h1.446c.316 0 .554-.293.417-.579a2.5 2.5 0 0 0-2.722-1.378c.374.51.653 1.09.813 1.72ZM14 7.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0ZM3.5 9a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM5 13c-.552 0-1.013-.455-.876-.99a4.002 4.002 0 0 1 7.753 0c.136.535-.324.99-.877.99H5Z"
						/>
					</svg>
				</div>
				<div class=" self-center">{$i18n.t('Feedbacks')}</div>
			</button>
		</div>

		<div class="flex-1 mt-1 lg:mt-0 overflow-y-scroll">
			{#if selectedTab === 'leaderboard'}
				<Leaderboard {feedbacks} />
			{:else if selectedTab === 'feedbacks'}
				<Feedbacks {feedbacks} />
			{/if}
		</div>
	</div>
{/if}
