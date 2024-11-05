<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	const dispatch = createEventDispatcher();

	import { getOllamaConfig, updateOllamaConfig } from '$lib/apis/ollama';
	import { getOpenAIConfig, updateOpenAIConfig, getOpenAIModels } from '$lib/apis/openai';
	import { getModels as _getModels } from '$lib/apis';

	import { models, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	import OpenAIConnection from './Connections/OpenAIConnection.svelte';
	import AddConnectionModal from './Connections/AddConnectionModal.svelte';
	import OllamaConnection from './Connections/OllamaConnection.svelte';

	const i18n = getContext('i18n');

	const getModels = async () => {
		const models = await _getModels(localStorage.token);
		return models;
	};

	// External
	let OLLAMA_BASE_URLS = [''];
	let OLLAMA_API_CONFIGS = {};

	let OPENAI_API_KEYS = [''];
	let OPENAI_API_BASE_URLS = [''];
	let OPENAI_API_CONFIGS = {};

	let ENABLE_OPENAI_API: null | boolean = null;
	let ENABLE_OLLAMA_API: null | boolean = null;

	let pipelineUrls = {};
	let showAddOpenAIConnectionModal = false;
	let showAddOllamaConnectionModal = false;

	const updateOpenAIHandler = async () => {
		if (ENABLE_OPENAI_API !== null) {
			OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.filter(
				(url, urlIdx) => OPENAI_API_BASE_URLS.indexOf(url) === urlIdx && url !== ''
			).map((url) => url.replace(/\/$/, ''));

			// Check if API KEYS length is same than API URLS length
			if (OPENAI_API_KEYS.length !== OPENAI_API_BASE_URLS.length) {
				// if there are more keys than urls, remove the extra keys
				if (OPENAI_API_KEYS.length > OPENAI_API_BASE_URLS.length) {
					OPENAI_API_KEYS = OPENAI_API_KEYS.slice(0, OPENAI_API_BASE_URLS.length);
				}

				// if there are more urls than keys, add empty keys
				if (OPENAI_API_KEYS.length < OPENAI_API_BASE_URLS.length) {
					const diff = OPENAI_API_BASE_URLS.length - OPENAI_API_KEYS.length;
					for (let i = 0; i < diff; i++) {
						OPENAI_API_KEYS.push('');
					}
				}
			}

			const res = await updateOpenAIConfig(localStorage.token, {
				ENABLE_OPENAI_API: ENABLE_OPENAI_API,
				OPENAI_API_BASE_URLS: OPENAI_API_BASE_URLS,
				OPENAI_API_KEYS: OPENAI_API_KEYS,
				OPENAI_API_CONFIGS: OPENAI_API_CONFIGS
			}).catch((error) => {
				toast.error(error);
			});

			if (res) {
				toast.success($i18n.t('OpenAI API settings updated'));
				await models.set(await getModels());
			}
		}
	};

	const updateOllamaHandler = async () => {
		if (ENABLE_OLLAMA_API !== null) {
			// Remove duplicate URLs
			OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.filter(
				(url, urlIdx) => OLLAMA_BASE_URLS.indexOf(url) === urlIdx && url !== ''
			).map((url) => url.replace(/\/$/, ''));

			console.log(OLLAMA_BASE_URLS);

			if (OLLAMA_BASE_URLS.length === 0) {
				ENABLE_OLLAMA_API = false;
				toast.info($i18n.t('Ollama API disabled'));
			}

			const res = await updateOllamaConfig(localStorage.token, {
				ENABLE_OLLAMA_API: ENABLE_OLLAMA_API,
				OLLAMA_BASE_URLS: OLLAMA_BASE_URLS,
				OLLAMA_API_CONFIGS: OLLAMA_API_CONFIGS
			}).catch((error) => {
				toast.error(error);
			});

			if (res) {
				toast.success($i18n.t('Ollama API settings updated'));
				await models.set(await getModels());
			}
		}
	};

	const addOpenAIConnectionHandler = async (connection) => {
		OPENAI_API_BASE_URLS = [...OPENAI_API_BASE_URLS, connection.url];
		OPENAI_API_KEYS = [...OPENAI_API_KEYS, connection.key];
		OPENAI_API_CONFIGS[connection.url] = connection.config;

		await updateOpenAIHandler();
	};

	const addOllamaConnectionHandler = async (connection) => {
		OLLAMA_BASE_URLS = [...OLLAMA_BASE_URLS, connection.url];
		OLLAMA_API_CONFIGS[connection.url] = connection.config;

		await updateOllamaHandler();
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			let ollamaConfig = {};
			let openaiConfig = {};

			await Promise.all([
				(async () => {
					ollamaConfig = await getOllamaConfig(localStorage.token);
				})(),
				(async () => {
					openaiConfig = await getOpenAIConfig(localStorage.token);
				})()
			]);

			ENABLE_OPENAI_API = openaiConfig.ENABLE_OPENAI_API;
			ENABLE_OLLAMA_API = ollamaConfig.ENABLE_OLLAMA_API;
			ENABLE_LDAP = ldapConfig.ENABLE_LDAP;

			OPENAI_API_BASE_URLS = openaiConfig.OPENAI_API_BASE_URLS;
			OPENAI_API_KEYS = openaiConfig.OPENAI_API_KEYS;
			OPENAI_API_CONFIGS = openaiConfig.OPENAI_API_CONFIGS;

			OLLAMA_BASE_URLS = ollamaConfig.OLLAMA_BASE_URLS;
			OLLAMA_API_CONFIGS = ollamaConfig.OLLAMA_API_CONFIGS;

			if (ENABLE_OPENAI_API) {
				for (const url of OPENAI_API_BASE_URLS) {
					if (!OPENAI_API_CONFIGS[url]) {
						OPENAI_API_CONFIGS[url] = {};
					}
				}

				OPENAI_API_BASE_URLS.forEach(async (url, idx) => {
					OPENAI_API_CONFIGS[url] = OPENAI_API_CONFIGS[url] || {};
					if (!(OPENAI_API_CONFIGS[url]?.enable ?? true)) {
						return;
					}
					const res = await getOpenAIModels(localStorage.token, idx);
					if (res.pipelines) {
						pipelineUrls[url] = true;
					}
				});
			}

			if (ENABLE_OLLAMA_API) {
				for (const url of OLLAMA_BASE_URLS) {
					if (!OLLAMA_API_CONFIGS[url]) {
						OLLAMA_API_CONFIGS[url] = {};
					}
				}
			}
		}
	});
</script>

<AddConnectionModal
	bind:show={showAddOpenAIConnectionModal}
	onSubmit={addOpenAIConnectionHandler}
/>

<AddConnectionModal
	ollama
	bind:show={showAddOllamaConnectionModal}
	onSubmit={addOllamaConnectionHandler}
/>

<form
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		updateOpenAIHandler();
		updateOllamaHandler();

		dispatch('save');
	}}
>
	<div class=" overflow-y-scroll scrollbar-hidden h-full">
		{#if ENABLE_OPENAI_API !== null && ENABLE_OLLAMA_API !== null}
			<div class="my-2">
				<div class="mt-2 space-y-2 pr-1.5">
					<div class="flex justify-between items-center text-sm">
						<div class="  font-medium">{$i18n.t('OpenAI API')}</div>

						<div class="flex items-center">
							<div class="">
								<Switch
									bind:state={ENABLE_OPENAI_API}
									on:change={async () => {
										updateOpenAIHandler();
									}}
								/>
							</div>
						</div>
					</div>

					{#if ENABLE_OPENAI_API}
						<hr class=" border-gray-50 dark:border-gray-850" />

						<div class="">
							<div class="flex justify-between items-center">
								<div class="font-medium">{$i18n.t('Manage OpenAI API Connections')}</div>

								<Tooltip content={$i18n.t(`Add Connection`)}>
									<button
										class="px-1"
										on:click={() => {
											showAddOpenAIConnectionModal = true;
										}}
										type="button"
									>
										<Plus />
									</button>
								</Tooltip>
							</div>

							<div class="flex flex-col gap-1.5 mt-1.5">
								{#each OPENAI_API_BASE_URLS as url, idx}
									<OpenAIConnection
										pipeline={pipelineUrls[url] ? true : false}
										bind:url
										bind:key={OPENAI_API_KEYS[idx]}
										bind:config={OPENAI_API_CONFIGS[url]}
										onSubmit={() => {
											updateOpenAIHandler();
										}}
										onDelete={() => {
											OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.filter(
												(url, urlIdx) => idx !== urlIdx
											);
											OPENAI_API_KEYS = OPENAI_API_KEYS.filter((key, keyIdx) => idx !== keyIdx);
										}}
									/>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>

			<hr class=" border-gray-50 dark:border-gray-850" />

			<div class="pr-1.5 my-2">
				<div class="flex justify-between items-center text-sm mb-2">
					<div class="  font-medium">{$i18n.t('Ollama API')}</div>

					<div class="mt-1">
						<Switch
							bind:state={ENABLE_OLLAMA_API}
							on:change={async () => {
								updateOllamaHandler();
							}}
						/>
					</div>
				</div>

				{#if ENABLE_OLLAMA_API}
					<hr class=" border-gray-50 dark:border-gray-850 my-2" />

					<div class="">
						<div class="flex justify-between items-center">
							<div class="font-medium">{$i18n.t('Manage Ollama API Connections')}</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									class="px-1"
									on:click={() => {
										showAddOllamaConnectionModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex w-full gap-1.5">
							<div class="flex-1 flex flex-col gap-1.5 mt-1.5">
								{#each OLLAMA_BASE_URLS as url, idx}
									<OllamaConnection
										bind:url
										bind:config={OLLAMA_API_CONFIGS[url]}
										{idx}
										onSubmit={() => {
											updateOllamaHandler();
										}}
										onDelete={() => {
											OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.filter((url, urlIdx) => idx !== urlIdx);
										}}
									/>
								{/each}
							</div>
						</div>

						<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('Trouble accessing Ollama?')}
							<a
								class=" text-gray-300 font-medium underline"
								href="https://github.com/open-webui/open-webui#troubleshooting"
								target="_blank"
							>
								{$i18n.t('Click here for help.')}
							</a>
						</div>
					</div>
				{/if}
			</div>

			<hr class=" dark:border-gray-850" />

			<div class=" space-y-3">
				<div class="mt-2 space-y-2 pr-1.5">
					<div class="flex justify-between items-center text-sm">
						<div class="  font-medium">{$i18n.t('LDAP')}</div>

						<div class="mt-1">
							<Switch
								bind:state={ENABLE_LDAP}
								on:change={async () => {
									updateLdapConfig(localStorage.token, ENABLE_LDAP);
								}}
							/>
						</div>
					</div>

					{#if ENABLE_LDAP}
						<div class="flex flex-col gap-1">
							<div class="flex w-full gap-2">
								<div class="w-full">
									<div class=" self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Label')}
									</div>
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
										required
										placeholder={$i18n.t('Enter server label')}
										bind:value={LDAP_SERVER.label}
									/>
								</div>
								<div class="w-full"></div>
							</div>
							<div class="flex w-full gap-2">
								<div class="w-full">
									<div class=" self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Host')}
									</div>
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
										required
										placeholder={$i18n.t('Enter server host')}
										bind:value={LDAP_SERVER.host}
									/>
								</div>
								<div class="w-full">
									<div class=" self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Port')}
									</div>
									<Tooltip
										placement="top-start"
										content={$i18n.t('Default to 389 or 636 if TLS is enabled')}
										className="w-full"
									>
										<input
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
											type="number"
											placeholder={$i18n.t('Enter server port')}
											bind:value={LDAP_SERVER.port}
										/>
									</Tooltip>
								</div>
							</div>
							<div class="flex w-full gap-2">
								<div class="w-full">
									<div class=" self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Application DN')}
									</div>
									<Tooltip
										content={$i18n.t('The Application Account DN you bind with for search')}
										placement="top-start"
									>
										<input
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
											required
											placeholder={$i18n.t('Enter Application DN')}
											bind:value={LDAP_SERVER.app_dn}
										/>
									</Tooltip>
								</div>
								<div class="w-full">
									<div class=" self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Application DN Password')}
									</div>
									<SensitiveInput
										placeholder={$i18n.t('Enter Application DN Password')}
										bind:value={LDAP_SERVER.app_dn_password}
									/>
								</div>
							</div>
							<div class="flex w-full gap-2">
								<div class="w-full">
									<div class=" self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Attribute for Username')}
									</div>
									<Tooltip
										content={$i18n.t(
											'The LDAP attribute that maps to the username that users use to sign in.'
										)}
										placement="top-start"
									>
										<input
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
											required
											placeholder={$i18n.t('Example: sAMAccountName or uid or userPrincipalName')}
											bind:value={LDAP_SERVER.attribute_for_username}
										/>
									</Tooltip>
								</div>
							</div>
							<div class="flex w-full gap-2">
								<div class="w-full">
									<div class=" self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Search Base')}
									</div>
									<Tooltip content={$i18n.t('The base to search for users')} placement="top-start">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
											required
											placeholder={$i18n.t('Example: ou=users,dc=foo,dc=example')}
											bind:value={LDAP_SERVER.search_base}
										/>
									</Tooltip>
								</div>
							</div>
							<div class="flex w-full gap-2">
								<div class="w-full">
									<div class=" self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Search Filters')}
									</div>
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
										placeholder={$i18n.t('Example: (&(objectClass=inetOrgPerson)(uid=%s))')}
										bind:value={LDAP_SERVER.search_filters}
									/>
								</div>
							</div>
							<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
								<a
									class=" text-gray-300 font-medium underline"
									href="https://ldap.com/ldap-filters/"
									target="_blank"
								>
									{$i18n.t('Click here for filter guides.')}
								</a>
							</div>
							<div>
								<div class="flex justify-between items-center text-sm">
									<div class="  font-medium">{$i18n.t('TLS')}</div>

									<div class="mt-1">
										<Switch bind:state={LDAP_SERVER.use_tls} />
									</div>
								</div>
								{#if LDAP_SERVER.use_tls}
									<div class="flex w-full gap-2">
										<div class="w-full">
											<div class=" self-center text-xs font-medium min-w-fit mb-1 mt-1">
												{$i18n.t('Certificate Path')}
											</div>
											<input
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
												required
												placeholder={$i18n.t('Enter certificate path')}
												bind:value={LDAP_SERVER.certificate_path}
											/>
										</div>
									</div>
									<div class="flex w-full gap-2">
										<div class="w-full">
											<div class=" self-center text-xs font-medium min-w-fit mb-1">
												{$i18n.t('Ciphers')}
											</div>
											<Tooltip content={$i18n.t('Default to ALL')} placement="top-start">
												<input
													class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													placeholder={$i18n.t('Example: ALL')}
													bind:value={LDAP_SERVER.ciphers}
												/>
											</Tooltip>
										</div>
										<div class="w-full"></div>
									</div>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</div>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
