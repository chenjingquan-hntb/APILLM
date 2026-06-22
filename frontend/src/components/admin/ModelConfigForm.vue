<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { ModelConfig, ModelConfigCreate, ModelConfigUpdate } from '@/types'

const props = defineProps<{
  modelConfig: ModelConfig | null
}>()

const emit = defineEmits<{
  submit: [data: ModelConfigCreate | ModelConfigUpdate]
}>()

const form = reactive<ModelConfigCreate>({
  model_id: '',
  display_name: '',
  group_name: '',
  description: '',
  icon: '',
  manual_prompt_price: null,
  manual_completion_price: null,
  is_enabled: true,
  sort_order: 0,
})

watch(
  () => props.modelConfig,
  (m) => {
    if (m) {
      form.model_id = m.model_id
      form.display_name = m.display_name ?? ''
      form.group_name = m.group_name ?? ''
      form.description = m.description ?? ''
      form.icon = m.icon ?? ''
      form.manual_prompt_price = m.manual_prompt_price
      form.manual_completion_price = m.manual_completion_price
      form.is_enabled = m.is_enabled
      form.sort_order = m.sort_order
    } else {
      form.model_id = ''
      form.display_name = ''
      form.group_name = ''
      form.description = ''
      form.icon = ''
      form.manual_prompt_price = null
      form.manual_completion_price = null
      form.is_enabled = true
      form.sort_order = 0
    }
  },
  { immediate: true }
)

function onSubmit() {
  const payload: ModelConfigCreate | ModelConfigUpdate = { ...form }
  if (!props.modelConfig) {
    emit('submit', payload as ModelConfigCreate)
  } else {
    emit('submit', payload as ModelConfigUpdate)
  }
}
</script>

<template>
  <el-form label-position="top">
    <el-form-item label="模型ID">
      <el-input v-model="form.model_id" placeholder="gpt-4o" />
    </el-form-item>

    <el-form-item label="展示名">
      <el-input v-model="form.display_name" />
    </el-form-item>

    <el-form-item label="分组">
      <el-input v-model="form.group_name" placeholder="GPT Series" />
    </el-form-item>

    <el-form-item label="手动价格 (prompt / Kt)">
      <el-input-number v-model="form.manual_prompt_price" :min="0" :step="0.00001" style="width: 100%" />
    </el-form-item>

    <el-form-item label="手动价格 (completion / Kt)">
      <el-input-number v-model="form.manual_completion_price" :min="0" :step="0.00001" style="width: 100%" />
    </el-form-item>

    <el-form-item label="启用">
      <el-switch v-model="form.is_enabled" />
    </el-form-item>

    <el-button type="primary" @click="onSubmit">保存</el-button>
  </el-form>
</template>
