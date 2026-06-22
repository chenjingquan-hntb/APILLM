<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { Upstream, UpstreamCreate, UpstreamUpdate } from '@/types'

const props = defineProps<{
  upstream: Upstream | null
}>()

const emit = defineEmits<{
  submit: [data: UpstreamCreate | UpstreamUpdate]
}>()

const form = reactive<UpstreamCreate>({
  name: '',
  base_url: '',
  api_key: '',
  protocol: 'openai',
  priority: 10,
  markup_rate: 0.2,
  is_enabled: true,
  pricing_config: null,
})

watch(
  () => props.upstream,
  (u) => {
    if (u) {
      form.name = u.name
      form.base_url = u.base_url
      form.api_key = u.api_key
      form.protocol = u.protocol
      form.priority = u.priority
      form.markup_rate = u.markup_rate
      form.is_enabled = u.is_enabled
      form.pricing_config = u.pricing_config
    } else {
      form.name = ''
      form.base_url = ''
      form.api_key = ''
      form.protocol = 'openai'
      form.priority = 10
      form.markup_rate = 0.2
      form.is_enabled = true
      form.pricing_config = null
    }
  },
  { immediate: true }
)

watch(() => form.protocol, () => {
  fillTemplate(form.protocol)
})

function fillTemplate(type: string) {
  if (type === 'none') {
    form.pricing_config = null
  } else {
    form.pricing_config = {
      model_id_field: 'id',
      prompt_price_field: 'pricing.prompt',
      completion_price_field: 'pricing.completion',
    }
  }
}

function onSubmit() {
  const payload: UpstreamCreate | UpstreamUpdate = { ...form }
  if (!props.upstream) {
    emit('submit', payload as UpstreamCreate)
  } else {
    emit('submit', payload as UpstreamUpdate)
  }
}

function stringifyConfig() {
  return JSON.stringify(form.pricing_config || {}, null, 2)
}

function updateConfigFromString(value: string) {
  try {
    form.pricing_config = value.trim() ? JSON.parse(value) : null
  } catch {
    // keep old value if invalid
  }
}
</script>

<template>
  <el-form label-position="top">
    <el-form-item label="名称">
      <el-input v-model="form.name" placeholder="例如：OpenAI 生产" />
    </el-form-item>

    <el-form-item label="地址">
      <el-input v-model="form.base_url" placeholder="https://api.openai.com" />
    </el-form-item>

    <el-form-item label="API Key">
      <el-input v-model="form.api_key" type="password" placeholder="sk-..." show-password />
    </el-form-item>

    <el-form-item label="协议">
      <el-select v-model="form.protocol" style="width: 100%">
        <el-option label="openai (OpenAI / OneAPI / NewAPI)" value="openai" />
        <el-option label="anthropic" value="anthropic" />
      </el-select>
    </el-form-item>

    <el-form-item label="加价率">
      <el-input-number v-model="form.markup_rate" :min="0" :step="0.01" style="width: 100%" />
    </el-form-item>

    <el-form-item label="优先级">
      <el-input-number v-model="form.priority" :min="0" :step="1" style="width: 100%" />
    </el-form-item>

    <el-form-item label="启用">
      <el-switch v-model="form.is_enabled" />
    </el-form-item>

    <el-form-item label="价格提取配置 (JSON)">
      <el-input
        type="textarea"
        :rows="5"
        :model-value="stringifyConfig()"
        style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem"
        placeholder='{"model_id_field":"id","prompt_price_field":"pricing.prompt","completion_price_field":"pricing.completion"}'
        @input="updateConfigFromString($event)"
      />
      <div class="template-links">
        常用模板：
        <a @click="fillTemplate('openai')">OneAPI/NewAPI</a> ·
        <a @click="fillTemplate('anthropic')">Anthropic</a> ·
        <a @click="fillTemplate('none')">仅模型名(无价格)</a>
      </div>
    </el-form-item>

    <el-button type="primary" @click="onSubmit">保存</el-button>
  </el-form>
</template>

<style scoped>
.template-links {
  margin-top: 0.25rem;
  font-size: 0.6875rem;
  color: var(--text-muted);
}

.template-links a {
  color: var(--accent-blue);
  cursor: pointer;
}

.template-links a:hover {
  color: var(--accent-blue-hover);
}
</style>
